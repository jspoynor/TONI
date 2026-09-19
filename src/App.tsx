import { useEffect, useState } from 'react'
import { Menu } from 'lucide-react'
import Sidebar from './components/Sidebar'
import EmptyState from './components/EmptyState'
import MessageList from './components/MessageList'
import { listConversations } from './lib/conversationStore'
import type { Conversation } from './types'
import './App.css'

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null)
  // Only meaningful below the mobile breakpoint — the Sidebar ignores it
  // entirely above that via CSS media query (see Sidebar.css).
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false)

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

  useEffect(() => {
    refreshConversations()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
        {activeConversationId === null ? (
          <EmptyState />
        ) : (
          <MessageList messages={activeConversation?.messages ?? []} />
        )}
      </main>
    </div>
  )
}

export default App
