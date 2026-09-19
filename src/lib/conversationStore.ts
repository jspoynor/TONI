import type { Attachment, ChatMessage, Conversation, Folder } from '../types'

/**
 * `Attachment.file` holds a `File`, which cannot survive a round trip through
 * `JSON.stringify`/`localStorage` (it would silently serialize to `{}`). Before
 * writing to storage we strip the `file` field from every attachment but keep
 * `name`/`type`/`size` so the UI can still show "this message had an attachment
 * named X" after a reload, even though the underlying bytes are gone. When
 * reading back we rebuild an empty placeholder `File` so the in-memory shape
 * still matches the `Attachment` type exactly.
 */
type StoredAttachment = Omit<Attachment, 'file'>

type StoredChatMessage = Omit<ChatMessage, 'attachments'> & {
  attachments?: StoredAttachment[]
}

type StoredConversation = Omit<Conversation, 'messages'> & {
  messages: StoredChatMessage[]
}

function stripAttachmentFile(attachment: Attachment): StoredAttachment {
  const { file: _file, ...rest } = attachment
  return rest
}

function toStoredMessage(message: ChatMessage): StoredChatMessage {
  return {
    ...message,
    attachments: message.attachments?.map(stripAttachmentFile),
  }
}

function fromStoredAttachment(attachment: StoredAttachment): Attachment {
  return {
    ...attachment,
    // The real File contents don't survive persistence; reconstruct an empty
    // placeholder so callers still get a well-typed Attachment at runtime.
    file: new File([], attachment.name, { type: attachment.type }),
  }
}

function fromStoredMessage(message: StoredChatMessage): ChatMessage {
  return {
    ...message,
    attachments: message.attachments?.map(fromStoredAttachment),
  }
}

function readStore(storageKey: string): Conversation[] {
  let raw: string | null
  try {
    raw = localStorage.getItem(storageKey)
  } catch {
    return []
  }

  if (!raw) return []

  try {
    const parsed = JSON.parse(raw) as StoredConversation[]
    if (!Array.isArray(parsed)) return []

    return parsed.map((conversation) => ({
      ...conversation,
      messages: conversation.messages.map(fromStoredMessage),
    }))
  } catch {
    return []
  }
}

function writeStore(storageKey: string, conversations: Conversation[]): void {
  const stored: StoredConversation[] = conversations.map((conversation) => ({
    ...conversation,
    messages: conversation.messages.map(toStoredMessage),
  }))

  try {
    localStorage.setItem(storageKey, JSON.stringify(stored))
  } catch {
    // Storage may be unavailable (private browsing, quota exceeded, etc.).
    // Swallow the error so save failures never crash the app.
  }
}

function generateId(): string {
  return crypto.randomUUID()
}

/**
 * Derives the folders storage key from a page's conversations storage key
 * (e.g. `toni:conversations` -> `toni:folders`), keeping `ChatPageConfig` to
 * a single `storageKey` field rather than adding a parallel one for folders.
 */
function foldersKey(storageKey: string): string {
  return `${storageKey.split(':')[0]}:folders`
}

function readFolders(storageKey: string): Folder[] {
  let raw: string | null
  try {
    raw = localStorage.getItem(foldersKey(storageKey))
  } catch {
    return []
  }

  if (!raw) return []

  try {
    const parsed = JSON.parse(raw) as Folder[]
    if (!Array.isArray(parsed)) return []

    return parsed
  } catch {
    return []
  }
}

function writeFolders(storageKey: string, folders: Folder[]): void {
  try {
    localStorage.setItem(foldersKey(storageKey), JSON.stringify(folders))
  } catch {
    // Storage may be unavailable (private browsing, quota exceeded, etc.).
    // Swallow the error so save failures never crash the app.
  }
}

/**
 * Derives a sidebar title from the first user message, matching Claude's own
 * convention of a short, truncated snippet of the opening message.
 */
function deriveTitle(content: string): string {
  const normalized = content.trim().replace(/\s+/g, ' ')
  if (!normalized) return 'New conversation'

  const MAX_LENGTH = 48
  if (normalized.length <= MAX_LENGTH) return normalized

  return `${normalized.slice(0, MAX_LENGTH).trimEnd()}…`
}

/** Returns all conversations, most recently updated first. */
export function listConversations(storageKey: string): Conversation[] {
  return readStore(storageKey).sort((a, b) => b.updatedAt - a.updatedAt)
}

/** Returns a single conversation by id, or `undefined` if it doesn't exist. */
export function getConversation(
  storageKey: string,
  id: string,
): Conversation | undefined {
  return readStore(storageKey).find((conversation) => conversation.id === id)
}

/**
 * Creates and persists a new conversation seeded with `firstMessage`. The
 * conversation's title is derived from that message's content. Callers should
 * only invoke this once a message is actually sent (not eagerly on "New
 * Chat") so empty conversations never clutter the sidebar.
 */
export function createConversation(
  storageKey: string,
  firstMessage: ChatMessage,
): Conversation {
  const now = Date.now()
  const conversation: Conversation = {
    id: generateId(),
    title: deriveTitle(firstMessage.content),
    messages: [firstMessage],
    createdAt: now,
    updatedAt: now,
  }

  const conversations = readStore(storageKey)
  conversations.push(conversation)
  writeStore(storageKey, conversations)

  return conversation
}

/**
 * Appends `message` to an existing conversation's message list, bumps
 * `updatedAt`, persists the change, and returns the updated conversation.
 * Throws if `conversationId` doesn't match an existing conversation.
 */
export function appendMessage(
  storageKey: string,
  conversationId: string,
  message: ChatMessage,
): Conversation {
  const conversations = readStore(storageKey)
  const index = conversations.findIndex((c) => c.id === conversationId)

  if (index === -1) {
    throw new Error(`Conversation not found: ${conversationId}`)
  }

  const updated: Conversation = {
    ...conversations[index],
    messages: [...conversations[index].messages, message],
    updatedAt: Date.now(),
  }

  conversations[index] = updated
  writeStore(storageKey, conversations)

  return updated
}

/** Generates a unique id suitable for a new `ChatMessage`. */
export function createMessageId(): string {
  return generateId()
}

/** Returns all folders for a page, newest-created first. */
export function listFolders(storageKey: string): Folder[] {
  return readFolders(storageKey).sort((a, b) => b.createdAt - a.createdAt)
}

/**
 * Creates and persists a new folder with the given (trimmed) name. New
 * folders default to `collapsed: false` (expanded) per spec.
 */
export function createFolder(storageKey: string, name: string): Folder {
  const folder: Folder = {
    id: generateId(),
    name: name.trim(),
    createdAt: Date.now(),
    collapsed: false,
  }

  const folders = readFolders(storageKey)
  folders.push(folder)
  writeFolders(storageKey, folders)

  return folder
}

/**
 * Updates and persists a folder's `collapsed` field. Throws if `folderId`
 * doesn't match an existing folder.
 */
export function setFolderCollapsed(
  storageKey: string,
  folderId: string,
  collapsed: boolean,
): Folder {
  const folders = readFolders(storageKey)
  const index = folders.findIndex((f) => f.id === folderId)

  if (index === -1) {
    throw new Error(`Folder not found: ${folderId}`)
  }

  const updated: Folder = { ...folders[index], collapsed }
  folders[index] = updated
  writeFolders(storageKey, folders)

  return updated
}

/**
 * One-time migration for conversations that predate folders. Finds
 * conversations with no `folderId`; if any exist, creates a "General" folder
 * and persists its id onto each of them (both the new `Folder` record and the
 * updated `Conversation` records are written back to storage). No-op if
 * there are no conversations, or if every conversation already has a
 * `folderId` (i.e. migration already ran).
 */
export function migrateFolderlessConversations(storageKey: string): void {
  const conversations = readStore(storageKey)
  const folderless = conversations.filter((c) => !c.folderId)

  if (folderless.length === 0) return

  const generalFolder = createFolder(storageKey, 'General')

  const migrated = conversations.map((conversation) =>
    conversation.folderId
      ? conversation
      : { ...conversation, folderId: generalFolder.id },
  )

  writeStore(storageKey, migrated)
}
