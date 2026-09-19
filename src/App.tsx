import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { Menu } from 'lucide-react'
import Sidebar from './components/Sidebar'
import EmptyState from './components/EmptyState'
import MessageList from './components/MessageList'
import InputArea from './components/InputArea'
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
import type { ChatMessage, ChatPageConfig, Conversation, Folder } from './types'
import './App.css'

interface AppProps {
  config: ChatPageConfig
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
        <InputArea
          name={config.name}
          onSend={handleSend}
          disabled={activeStreamingMessage !== null}
        />
      </main>
    </div>
  )
}

export default App
