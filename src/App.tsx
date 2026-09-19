import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { Menu } from 'lucide-react'
import Sidebar from './components/Sidebar'
import EmptyState from './components/EmptyState'
import MessageList from './components/MessageList'
import InputArea from './components/InputArea'
import QuestionPrompt from './components/QuestionPrompt'
import {
  appendMessage,
  createConversation,
  createFolder,
  createMessageId,
  listConversations,
  listFolders,
  migrateFolderlessConversations,
  setFolderCollapsed,
} from './lib/conversationStore'
import { sendMessage } from './lib/sendMessage'
import {
  ApiError,
  answerQuestion,
  getCompanies,
  getCompanyReports,
  getReport,
  pollJob,
  uploadDocument,
} from './lib/api'
import type {
  Attachment,
  ChatMessage,
  ChatPageConfig,
  Conversation,
  Folder,
  QuestionAnswer,
  QuestionQueue,
} from './types'
import './App.css'

interface AppProps {
  config: ChatPageConfig
}

/**
 * The one live reporting request a `reportIntegration`-enabled page (Anne)
 * is bootstrapped against. `conversationId` tracks which chat thread last
 * triggered upload/question activity, so `QuestionPrompt` only renders in
 * that thread rather than bleeding into unrelated conversations.
 */
interface ReportState {
  reportId: string
  revision: number
  currency: string
  periodStart: string
  periodEnd: string
  questionQueue: QuestionQueue
  conversationId: string | null
}

function App({ config }: AppProps) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [folders, setFolders] = useState<Folder[]>([])
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null)
  // Tracks which folder a pending (unsent) draft belongs to, i.e. while
  // `activeConversationId === null`. Set when the user opens a draft via
  // "New Folder" or a per-folder "new chat" button, consumed (and reset) once
  // `handleSend` turns that draft into a real, persisted conversation.
  const [pendingFolderId, setPendingFolderId] = useState<string | null>(null)
  // Only meaningful below the mobile breakpoint — the Sidebar ignores it
  // entirely above that via CSS media query (see Sidebar.css).
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false)
  // In-progress assistant replies for mock streams currently running,
  // keyed by the id of the conversation each one belongs to. Kept out of the
  // persisted store until each is complete (see `handleSend`) — this is
  // ephemeral UI state, appended to the visible message list but written to
  // `localStorage` only once, as a single final message. Keying by
  // conversationId (rather than a single bare `ChatMessage`) lets
  // `displayedMessages` only show a reply while its own conversation is the
  // active one — switching away mid-stream just hides it (it keeps
  // streaming and persists correctly in the background) instead of letting
  // it bleed into whatever conversation is currently on screen. A map (not a
  // single slot) also means two different conversations can stream
  // concurrently without one clobbering the other's in-progress state.
  const [streamingReplies, setStreamingReplies] = useState<
    Record<string, ChatMessage>
  >({})

  // Real backend state for `reportIntegration`-enabled pages only (Anne).
  // Stays `null`/`'idle'` forever on pages without it (Toni).
  const [reportState, setReportState] = useState<ReportState | null>(null)
  const [reportStatus, setReportStatus] = useState<
    'idle' | 'loading' | 'ready' | 'unavailable'
  >('idle')
  const [isUploading, setIsUploading] = useState(false)
  const [isAnswering, setIsAnswering] = useState(false)

  // Loads the conversation list on mount. Future tasks that mutate the store
  // (e.g. sending the first message of a new conversation) should call
  // `refreshConversations()` afterward to keep the sidebar in sync.
  const refreshConversations = () =>
    setConversations(listConversations(config.storageKey))

  // Mirrors `refreshConversations` for folders. A harmless no-op for pages
  // with folders disabled (Anne) — her folders key just stays empty.
  const refreshFolders = () => setFolders(listFolders(config.storageKey))

  // `listConversations()` already returns full `Conversation` objects
  // (including `messages`), so the active conversation's messages can be
  // derived directly without a separate store read.
  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeConversationId,
  )

  // While a reply is streaming for the conversation currently on screen,
  // render it as a trailing message appended to the real (persisted) list.
  // MessageList stays entirely unaware that streaming is a concept — it just
  // renders whatever array it's given. A stream in progress for some OTHER
  // conversation (the user switched away mid-reply) is intentionally not
  // shown here.
  const activeStreamingMessage = activeConversationId
    ? (streamingReplies[activeConversationId] ?? null)
    : null

  const displayedMessages = activeStreamingMessage
    ? [...(activeConversation?.messages ?? []), activeStreamingMessage]
    : (activeConversation?.messages ?? [])

  // The active folder: whichever folder contains the active conversation, or
  // (while a draft is open) whichever folder the pending draft belongs to.
  // Recomputed each render rather than tracked as its own state, since it's
  // fully derived from `activeConversationId`/`pendingFolderId`/`conversations`.
  const activeFolderId: string | null =
    activeConversationId === null
      ? pendingFolderId
      : (conversations.find(
          (conversation) => conversation.id === activeConversationId,
        )?.folderId ?? null)

  useEffect(() => {
    // Legacy Toni conversations may predate folders; migrate them into a
    // "General" folder before the first read so migrated data shows up in
    // the initial render. Anne never runs this (folders stay unsupported for
    // her data under any circumstance).
    if (config.foldersEnabled) {
      migrateFolderlessConversations(config.storageKey)
    }
    refreshConversations()
    refreshFolders()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    document.title = config.name
  }, [config.name])

  // Bootstraps the company's one "live" reporting request on mount, for
  // pages with `reportIntegration` configured. Any failure (network, 401,
  // no live report yet) just leaves the page on the mock reply — this must
  // never hard-block the chat.
  useEffect(() => {
    const integration = config.reportIntegration
    if (!integration) return
    let cancelled = false

    setReportStatus('loading')
    ;(async () => {
      const companies = await getCompanies(integration)
      const company = companies[0]
      if (!company) throw new Error('No company found for this token')

      const reports = await getCompanyReports(integration, company.id)
      const latest = reports
        .filter((r) => r.scenario === 'live')
        .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0]
      if (!latest) throw new Error('No active reporting request yet')

      const view = await getReport(integration, latest.id)
      if (!view.report || !view.question_queue) {
        throw new Error('Unexpected report shape')
      }
      if (cancelled) return

      setReportState({
        reportId: view.id,
        revision: view.revision,
        currency: view.report.request.currency,
        periodStart: view.report.request.period_start,
        periodEnd: view.report.request.period_end,
        questionQueue: view.question_queue,
        conversationId: null,
      })
      setReportStatus('ready')
    })().catch(() => {
      if (!cancelled) setReportStatus('unavailable')
    })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const pushAssistantMessage = (conversationId: string, content: string) => {
    appendMessage(config.storageKey, conversationId, {
      id: createMessageId(),
      role: 'assistant',
      content,
      createdAt: Date.now(),
    })
    refreshConversations()
  }

  /**
   * Real upload flow for `reportIntegration` pages: POSTs each attachment,
   * polls its scan job to completion, then refreshes the report and narrates
   * the outcome (including the next open question, if any) as ordinary
   * assistant chat messages. Runs instead of the mock reply — the backend
   * has no chat endpoint, so there's nothing else to send free text to for
   * an upload turn.
   */
  const handleRealUpload = async (
    conversationId: string,
    attachments: Attachment[],
  ) => {
    const integration = config.reportIntegration
    if (!integration || !reportState) return

    let revision = reportState.revision
    let questionQueue = reportState.questionQueue

    setIsUploading(true)
    try {
      for (const attachment of attachments) {
        try {
          const result = await uploadDocument(
            integration,
            reportState.reportId,
            attachment.file,
            revision,
          )
          revision = result.revision

          if (result.duplicate) {
            pushAssistantMessage(
              conversationId,
              `I already have **${attachment.name}** on file for this report — no new scan needed.`,
            )
            continue
          }

          pushAssistantMessage(
            conversationId,
            `Got **${attachment.name}** — scanning it now. I'll let you know what I find.`,
          )

          const job = result.job_id
            ? await pollJob(integration, result.job_id)
            : null

          if (!job) {
            pushAssistantMessage(
              conversationId,
              `Still scanning **${attachment.name}** — this is taking a while. I'll check again once you send your next message.`,
            )
            continue
          }

          if (job.status === 'failed') {
            pushAssistantMessage(
              conversationId,
              `That upload failed scanning: ${job.error ?? 'unknown error'}. Try a clearer document or a different file.`,
            )
            continue
          }

          const view = await getReport(integration, reportState.reportId)
          revision = view.revision
          questionQueue = view.question_queue ?? questionQueue
          const nextQuestion = questionQueue.questions[0]
          pushAssistantMessage(
            conversationId,
            nextQuestion
              ? nextQuestion.question
              : `Thanks! **${attachment.name}** is fully processed and there's nothing else needed from you right now.`,
          )
        } catch (error) {
          const detail =
            error instanceof ApiError
              ? error.detail
              : 'Something went wrong uploading that file.'
          pushAssistantMessage(
            conversationId,
            `**${attachment.name}** didn't go through: ${detail}`,
          )
          // Best-effort resync so a stale revision doesn't also fail the
          // next attachment in this same batch.
          try {
            const view = await getReport(integration, reportState.reportId)
            revision = view.revision
            questionQueue = view.question_queue ?? questionQueue
          } catch {
            // Ignore — the next attempt will surface its own error.
          }
        }
      }
    } finally {
      setReportState((prev) =>
        prev ? { ...prev, revision, questionQueue, conversationId } : prev,
      )
      setIsUploading(false)
    }
  }

  /** Submits a structured answer for the current top question (see `QuestionPrompt`). */
  const handleAnswerQuestion = async (
    answer: QuestionAnswer,
    message: string,
  ) => {
    const integration = config.reportIntegration
    if (!integration || !reportState || !reportState.conversationId) return
    const conversationId = reportState.conversationId
    const question = reportState.questionQueue.questions[0]
    if (!question) return

    appendMessage(config.storageKey, conversationId, {
      id: createMessageId(),
      role: 'user',
      content: message,
      createdAt: Date.now(),
    })
    refreshConversations()

    setIsAnswering(true)
    try {
      const result = await answerQuestion(
        integration,
        reportState.reportId,
        question.question_id,
        answer,
        message,
        reportState.revision,
      )
      setReportState((prev) =>
        prev
          ? {
              ...prev,
              revision: result.revision,
              questionQueue: result.question_queue,
            }
          : prev,
      )
      const next = result.question_queue.questions[0]
      pushAssistantMessage(
        conversationId,
        next
          ? `Got it, thanks.\n\n${next.question}`
          : "Got it, thanks — that's everything I need for now.",
      )
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        try {
          const view = await getReport(integration, reportState.reportId)
          if (view.question_queue) {
            setReportState((prev) =>
              prev
                ? {
                    ...prev,
                    revision: view.revision,
                    questionQueue: view.question_queue!,
                  }
                : prev,
            )
          }
          pushAssistantMessage(
            conversationId,
            'The report changed elsewhere — I refreshed it. Please try answering again.',
          )
        } catch {
          pushAssistantMessage(
            conversationId,
            "Couldn't refresh the report — please try again in a moment.",
          )
        }
      } else {
        const detail =
          error instanceof ApiError
            ? error.detail
            : 'Something went wrong sending that answer.'
        pushAssistantMessage(conversationId, `That answer didn't go through: ${detail}`)
      }
    } finally {
      setIsAnswering(false)
    }
  }

  /**
   * Handles a submitted user message from `InputArea`. Creates a new
   * conversation on first send (or appends to the active one), then streams
   * the mock assistant reply in as ephemeral `streamingReplies` state keyed
   * to this conversation's id, persisting the final assistant message in one
   * shot once the stream completes. Captures `conversationId` in this
   * closure so the stream keeps updating/persisting to the right
   * conversation even if the user switches away (or sends a message in
   * another conversation) before it finishes.
   */
  const handleSend = async (message: ChatMessage) => {
    let conversationId = activeConversationId
    let conversation: Conversation

    if (conversationId === null) {
      conversation = createConversation(
        config.storageKey,
        message,
        pendingFolderId ?? undefined,
      )
      conversationId = conversation.id
      setActiveConversationId(conversationId)
      setPendingFolderId(null)
    } else {
      conversation = appendMessage(config.storageKey, conversationId, message)
    }
    refreshConversations()

    const attachments = message.attachments ?? []

    // Real backend flow (Anne only, once bootstrapped): attachments go to
    // the actual upload/scan/question pipeline instead of the mock reply.
    // Plain text with no attachment still falls through to the mock reply
    // below — the backend has nothing to interpret free text against.
    if (
      config.reportIntegration &&
      reportStatus === 'ready' &&
      reportState &&
      attachments.length > 0
    ) {
      await handleRealUpload(conversationId, attachments)
      return
    }

    const assistantId = createMessageId()
    const assistantCreatedAt = Date.now()
    let assistantContent = ''

    const setStreamingContent = (content: string) =>
      setStreamingReplies((prev) => ({
        ...prev,
        [conversationId]: {
          id: assistantId,
          role: 'assistant',
          content,
          createdAt: assistantCreatedAt,
        },
      }))

    setStreamingContent('')

    for await (const chunk of sendMessage(
      conversation.messages,
      attachments,
      config.mockReplyText,
    )) {
      assistantContent += chunk
      setStreamingContent(assistantContent)
    }

    appendMessage(config.storageKey, conversationId, {
      id: assistantId,
      role: 'assistant',
      content: assistantContent,
      createdAt: assistantCreatedAt,
    })
    refreshConversations()
    setStreamingReplies((prev) => {
      const { [conversationId]: _finished, ...rest } = prev
      return rest
    })
  }

  // Creates and persists a new folder, then opens a draft scoped to it —
  // mirrors the pre-folders "New Chat" behavior (`activeConversationId` goes
  // to `null`), just also tracking which folder the draft belongs to.
  const handleCreateFolder = (name: string) => {
    const folder = createFolder(config.storageKey, name)
    refreshFolders()
    setActiveConversationId(null)
    setPendingFolderId(folder.id)
  }

  // The per-folder "new chat" button: identical shape to the old top-level
  // "New Chat" button, just scoped to a specific folder.
  const handleNewChatInFolder = (folderId: string) => {
    setActiveConversationId(null)
    setPendingFolderId(folderId)
  }

  const handleToggleFolderCollapse = (folderId: string) => {
    const folder = folders.find((f) => f.id === folderId)
    if (!folder) return
    setFolderCollapsed(config.storageKey, folderId, !folder.collapsed)
    refreshFolders()
  }

  return (
    <div
      id="app"
      style={
        {
          '--accent': config.accent,
          '--accent-bg': config.accentBg,
          '--accent-border': config.accentBorder,
        } as CSSProperties
      }
    >
      <Sidebar
        name={config.name}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={setActiveConversationId}
        onNewChat={() => setActiveConversationId(null)}
        isOpen={isMobileDrawerOpen}
        onClose={() => setIsMobileDrawerOpen(false)}
        foldersEnabled={config.foldersEnabled}
        folders={folders}
        activeFolderId={activeFolderId}
        onCreateFolder={handleCreateFolder}
        onNewChatInFolder={handleNewChatInFolder}
        onToggleFolderCollapse={handleToggleFolderCollapse}
      />
      <main className="main-panel">
        <header className="mobile-topbar">
          <button
            type="button"
            className="mobile-menu-toggle"
            aria-label="Open sidebar"
            onClick={() => setIsMobileDrawerOpen(true)}
          >
            <Menu size={22} strokeWidth={1.75} aria-hidden="true" />
          </button>
        </header>
        <div className="main-content">
          {activeConversationId === null ? (
            <EmptyState greeting={config.emptyStateGreeting} />
          ) : (
            <MessageList messages={displayedMessages} />
          )}
        </div>
        {activeConversationId !== null &&
          reportState?.conversationId === activeConversationId &&
          reportState.questionQueue.questions[0] && (
            <QuestionPrompt
              key={reportState.questionQueue.questions[0].question_id}
              question={reportState.questionQueue.questions[0]}
              currency={reportState.currency}
              periodStart={reportState.periodStart}
              periodEnd={reportState.periodEnd}
              disabled={isAnswering}
              onSubmit={handleAnswerQuestion}
            />
          )}
        <InputArea
          name={config.name}
          onSend={handleSend}
          disabled={activeStreamingMessage !== null || isUploading}
        />
      </main>
    </div>
  )
}

export default App
