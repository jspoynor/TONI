import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar'
import { listConversations } from './lib/conversationStore'
import type { Conversation } from './types'
import './App.css'

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null)

  // Loads the conversation list on mount. Future tasks that mutate the store
  // (e.g. sending the first message of a new conversation) should call
  // `refreshConversations()` afterward to keep the sidebar in sync.
  const refreshConversations = () => setConversations(listConversations())

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
      />
      <main className="main-panel">
        <p>Main panel — Task 7 builds this</p>
      </main>
    </div>
  )
}

export default App
