import { useEffect, useState } from 'react'
import { Menu } from 'lucide-react'
import Sidebar from './components/Sidebar'
import EmptyState from './components/EmptyState'
import MessageList from './components/MessageList'
import InputArea from './components/InputArea'
import {
  appendMessage,
  createConversation,
  createMessageId,
  listConversations,
} from './lib/conversationStore'
import { sendMessage } from './lib/sendMessage'
import type { ChatMessage, Conversation } from './types'
import './App.css'

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null)
  // Only meaningful below the mobile breakpoint — the Sidebar ignores it
  // entirely above that via CSS media query (see Sidebar.css).
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false)
  // The in-progress assistant reply while a mock stream is running. Kept out
  // of the persisted store until it's complete (see `handleSend`) — this is
  // ephemeral UI state, appended to the visible message list but written to
  // `localStorage` only once, as a single final message.
  const [streamingMessage, setStreamingMessage] = useState<ChatMessage | null>(
    null,
  )

  // Loads the conversation list on mount. Future tasks that mutate the store
  // (e.g. sending the first message of a new conversation) should call
  // `refreshConversations()` afterward to keep the sidebar in sync.
  const refreshConversations = () => setConversations(listConversations())

  // `listConversations()` already returns full `Conversation` objects
  // (including `messages`), so the active conversation's messages can be
  // derived directly without a separate store read.
  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeConversationId,
  )

  // While a reply is streaming, render it as a trailing message appended to
  // the real (persisted) list. MessageList stays entirely unaware that
  // streaming is a concept — it just renders whatever array it's given.
  const displayedMessages = streamingMessage
    ? [...(activeConversation?.messages ?? []), streamingMessage]
    : (activeConversation?.messages ?? [])

  useEffect(() => {
    refreshConversations()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /**
   * Handles a submitted user message from `InputArea`. Creates a new
   * conversation on first send (or appends to the active one), then streams
   * the mock assistant reply in as ephemeral `streamingMessage` state,
   * persisting the final assistant message in one shot once the stream
   * completes.
   */
  const handleSend = async (message: ChatMessage) => {
    let conversationId = activeConversationId
    let conversation: Conversation

    if (conversationId === null) {
      conversation = createConversation(message)
      conversationId = conversation.id
      setActiveConversationId(conversationId)
    } else {
      conversation = appendMessage(conversationId, message)
    }
    refreshConversations()

    const attachments = message.attachments ?? []
    const assistantId = createMessageId()
    const assistantCreatedAt = Date.now()
    let assistantContent = ''

    setStreamingMessage({
      id: assistantId,
      role: 'assistant',
      content: '',
      createdAt: assistantCreatedAt,
    })

    for await (const chunk of sendMessage(conversation.messages, attachments)) {
      assistantContent += chunk
      setStreamingMessage({
        id: assistantId,
        role: 'assistant',
        content: assistantContent,
        createdAt: assistantCreatedAt,
      })
    }

    appendMessage(conversationId, {
      id: assistantId,
      role: 'assistant',
      content: assistantContent,
      createdAt: assistantCreatedAt,
    })
    refreshConversations()
    setStreamingMessage(null)
  }

  return (
    <div id="app">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={setActiveConversationId}
        onNewChat={() => setActiveConversationId(null)}
        isOpen={isMobileDrawerOpen}
        onClose={() => setIsMobileDrawerOpen(false)}
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
            <EmptyState />
          ) : (
            <MessageList messages={displayedMessages} />
          )}
        </div>
        <InputArea onSend={handleSend} disabled={streamingMessage !== null} />
      </main>
    </div>
  )
}

export default App
