import { SquarePen, CircleUserRound } from 'lucide-react'
import type { Conversation } from '../types'
import './Sidebar.css'

export interface SidebarProps {
  conversations: Conversation[]
  activeConversationId: string | null
  onSelectConversation: (id: string) => void
  onNewChat: () => void
}

function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <h1 className="sidebar-wordmark">Toni</h1>

      <button type="button" className="sidebar-new-chat" onClick={onNewChat}>
        <SquarePen size={18} strokeWidth={1.75} aria-hidden="true" />
        New Chat
      </button>

      <nav className="sidebar-conversations" aria-label="Conversations">
        <ul>
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <button
                type="button"
                className={
                  conversation.id === activeConversationId
                    ? 'sidebar-conversation sidebar-conversation--active'
                    : 'sidebar-conversation'
                }
                aria-current={
                  conversation.id === activeConversationId ? 'true' : undefined
                }
                onClick={() => onSelectConversation(conversation.id)}
              >
                {conversation.title}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="sidebar-user">
        <span className="sidebar-user-avatar" aria-hidden="true">
          <CircleUserRound size={20} strokeWidth={1.5} />
        </span>
        <span className="sidebar-user-name">Guest</span>
      </div>
    </aside>
  )
}

export default Sidebar
