import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import {
  SquarePen,
  FolderPlus,
  ChevronRight,
  ChevronDown,
  CircleUserRound,
} from 'lucide-react'
import type { Conversation, Folder } from '../types'
import './Sidebar.css'

export interface SidebarProps {
  name: string
  conversations: Conversation[]
  activeConversationId: string | null
  onSelectConversation: (id: string) => void
  onNewChat: () => void
  isOpen: boolean
  onClose: () => void
  foldersEnabled?: boolean
  folders: Folder[]
  activeFolderId: string | null
  onCreateFolder: (name: string) => void
  onNewChatInFolder: (folderId: string) => void
  onToggleFolderCollapse: (folderId: string) => void
}

function Sidebar({
  name,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  isOpen,
  onClose,
  foldersEnabled,
  folders,
  activeFolderId,
  onCreateFolder,
  onNewChatInFolder,
  onToggleFolderCollapse,
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

  // Whether the inline "name your new folder" row is currently showing at
  // the top of the folder list. Local, transient UI state — nothing is
  // created until the row is committed.
  const [isCreatingFolder, setIsCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')

  const handleStartCreateFolder = () => {
    setNewFolderName('')
    setIsCreatingFolder(true)
  }

  const commitOrCancelNewFolder = () => {
    const trimmed = newFolderName.trim()
    if (trimmed) {
      onCreateFolder(trimmed)
      onClose()
    }
    setIsCreatingFolder(false)
    setNewFolderName('')
  }

  const cancelNewFolder = () => {
    setIsCreatingFolder(false)
    setNewFolderName('')
  }

  const handleNewFolderInputKeyDown = (
    event: KeyboardEvent<HTMLInputElement>,
  ) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      commitOrCancelNewFolder()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      cancelNewFolder()
    }
  }

  const handleNewChatInFolder = (folderId: string) => {
    onNewChatInFolder(folderId)
    onClose()
  }

  // Used only by the folders-enabled path below to render each folder's
  // nested chat list, with the same markup/active-state logic as the flat
  // list's own `<li>`/button below (which stays inline and untouched so
  // Anne's rendering path is unaffected).
  const renderFolderConversationList = (list: Conversation[]) => (
    <ul>
      {list.map((conversation) => (
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
            onClick={() => handleSelectConversation(conversation.id)}
          >
            {conversation.title}
          </button>
        </li>
      ))}
    </ul>
  )

  return (
    <>
      <aside
        className={
          isOpen ? 'sidebar sidebar--open' : 'sidebar'
        }
      >
        <h1 className="sidebar-wordmark">{name}</h1>

        {foldersEnabled ? (
          <>
            <button
              type="button"
              className="sidebar-new-chat"
              onClick={handleStartCreateFolder}
            >
              <FolderPlus size={18} strokeWidth={1.75} aria-hidden="true" />
              New Folder
            </button>

            <nav className="sidebar-conversations" aria-label="Folders">
              {isCreatingFolder && (
                <div className="sidebar-folder-new">
                  <input
                    type="text"
                    className="sidebar-folder-new-input"
                    autoFocus
                    value={newFolderName}
                    onChange={(event) => setNewFolderName(event.target.value)}
                    onKeyDown={handleNewFolderInputKeyDown}
                    onBlur={commitOrCancelNewFolder}
                    aria-label="New folder name"
                  />
                </div>
              )}

              {folders.map((folder) => {
                const folderConversations = conversations.filter(
                  (conversation) => conversation.folderId === folder.id,
                )
                const isActiveFolder = folder.id === activeFolderId

                return (
                  <div key={folder.id} className="sidebar-folder">
                    <button
                      type="button"
                      className={
                        isActiveFolder
                          ? 'sidebar-folder-header sidebar-folder-header--active'
                          : 'sidebar-folder-header'
                      }
                      aria-current={isActiveFolder ? 'true' : undefined}
                      aria-expanded={!folder.collapsed}
                      onClick={() => onToggleFolderCollapse(folder.id)}
                    >
                      {folder.collapsed ? (
                        <ChevronRight
                          size={16}
                          strokeWidth={1.75}
                          aria-hidden="true"
                        />
                      ) : (
                        <ChevronDown
                          size={16}
                          strokeWidth={1.75}
                          aria-hidden="true"
                        />
                      )}
                      <span className="sidebar-folder-name">
                        {folder.name}
                      </span>
                    </button>

                    {!folder.collapsed && (
                      <>
                        {renderFolderConversationList(folderConversations)}
                        <button
                          type="button"
                          className="sidebar-folder-new-chat"
                          onClick={() => handleNewChatInFolder(folder.id)}
                        >
                          <SquarePen
                            size={14}
                            strokeWidth={1.75}
                            aria-hidden="true"
                          />
                          New chat
                        </button>
                      </>
                    )}
                  </div>
                )
              })}
            </nav>
          </>
        ) : (
          <>
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
          </>
        )}

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
