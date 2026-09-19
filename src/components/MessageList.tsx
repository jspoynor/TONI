import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Paperclip } from 'lucide-react'
import type { ChatMessage } from '../types'
import './MessageList.css'

export interface MessageListProps {
  messages: ChatMessage[]
}

/**
 * Renders the active conversation's messages, applying Markdown (including
 * fenced code blocks) to each message's content and distinct styling for
 * user vs. assistant roles. Auto-scrolls to the newest message whenever the
 * list changes, which also covers chunks arriving during a streamed reply.
 */
function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  return (
    <div className="message-list">
      {messages.map((message) => (
        <div key={message.id} className={`message message--${message.role}`}>
          <div className="message-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
          {message.attachments && message.attachments.length > 0 && (
            <div className="message-attachments">
              {message.attachments.map((attachment, index) => (
                <span
                  className="message-attachment-chip"
                  key={`${message.id}-attachment-${index}`}
                >
                  <Paperclip size={14} strokeWidth={1.75} aria-hidden="true" />
                  {attachment.name}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

export default MessageList
