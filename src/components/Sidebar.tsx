import { SquarePen, CircleUserRound } from 'lucide-react'
import type { Conversation } from '../types'
import './Sidebar.css'

export interface SidebarProps {
  conversations: Conversation[]
  activeConversationId: string | null
  onSelectConversation: (id: string) => void
  onNewChat: () => void
  isOpen: boolean
  onClose: () => void
}

function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  isOpen,
  onClose,
}: SidebarProps) {
  // Below the mobile breakpoint the sidebar is an off-canvas drawer, so
  // selecting a conversation or starting a new chat should also close it and
  // return the user to the chat view. Above the breakpoint `onClose` is a
  // harmless no-op state update (the sidebar is always visible there).
  const handleSelectConversation = (id: string) => {
    onSelectConversation(id)
    onClose()
  }

  const handleNewChat = () => {
    onNewChat()
    onClose()
  }

  return (
    <>
      <aside
        className={
          isOpen ? 'sidebar sidebar--open' : 'sidebar'
        }
      >
        <h1 className="sidebar-wordmark">Toni</h1>

        <button
          type="button"
          className="sidebar-new-chat"
          onClick={handleNewChat}
        >
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
                    conversation.id === activeConversationId
                      ? 'true'
                      : undefined
                  }
                  onClick={() => handleSelectConversation(conversation.id)}
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

      {isOpen && (
        <div
          className="sidebar-scrim"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
    </>
  )
}

export default Sidebar
