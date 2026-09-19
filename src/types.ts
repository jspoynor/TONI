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
