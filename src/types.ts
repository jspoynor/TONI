export interface Attachment {
  name: string
  type: string
  size: number
  file: File
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  attachments?: Attachment[]
  createdAt: number
}

export interface Conversation {
  id: string
  title: string // derived from the first user message
  messages: ChatMessage[]
  createdAt: number
  updatedAt: number
}

export interface ChatPageConfig {
  name: string // "Toni" | "Anne" — wordmark, placeholder, mock reply text
  storageKey: string // localStorage key for this page's conversations
  accent: string // e.g. "#c084fc" | "#f472b6"
  accentBg: string // rgba tint derived from accent
  accentBorder: string // rgba tint derived from accent
  emptyStateGreeting: string
  mockReplyText: string
}
