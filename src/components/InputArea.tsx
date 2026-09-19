import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, KeyboardEvent } from 'react'
import { ArrowUp, File as FileIcon, Paperclip, X } from 'lucide-react'
import type { Attachment, ChatMessage } from '../types'
import { createMessageId } from '../lib/conversationStore'
import './InputArea.css'

export interface InputAreaProps {
  onSend: (message: ChatMessage) => void
  /** True while a reply is streaming for the currently active conversation, to prevent double-submit. */
  disabled: boolean
}

interface PendingAttachment {
  file: File
  /** Object URL for an image preview thumbnail, or `null` for non-image files. */
  previewUrl: string | null
}

const MAX_TEXTAREA_HEIGHT = 200

/**
 * Bottom-of-panel composer: a growable textarea, an attach-file button, a
 * removable chip row for files staged but not yet sent, and a send button.
 * Owns all of its own draft state (text + pending attachments); on submit it
 * assembles a `ChatMessage` and hands it to `onSend`, which is where the
 * caller (App) does the actual store/streaming work.
 */
function InputArea({ onSend, disabled }: InputAreaProps) {
  const [text, setText] = useState('')
  const [pendingAttachments, setPendingAttachments] = useState<
    PendingAttachment[]
  >([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Mirrors `pendingAttachments` so the unmount-cleanup effect below (which
  // must run only once, with an empty dependency array) can always see the
  // latest list rather than closing over the empty array from first render.
  const pendingAttachmentsRef = useRef<PendingAttachment[]>(pendingAttachments)
  useEffect(() => {
    pendingAttachmentsRef.current = pendingAttachments
  }, [pendingAttachments])

  // Revoke any outstanding object URLs if the component unmounts mid-draft,
  // so staged image previews never leak memory.
  useEffect(() => {
    return () => {
      pendingAttachmentsRef.current.forEach((attachment) => {
        if (attachment.previewUrl) URL.revokeObjectURL(attachment.previewUrl)
      })
    }
  }, [])

  const canSend =
    !disabled && (text.trim().length > 0 || pendingAttachments.length > 0)

  const handleFilesSelected = (files: FileList | null) => {
    if (!files || files.length === 0) return

    const next: PendingAttachment[] = Array.from(files).map((file) => ({
      file,
      previewUrl: file.type.startsWith('image/')
        ? URL.createObjectURL(file)
        : null,
    }))
    setPendingAttachments((prev) => [...prev, ...next])
  }

  const handleRemoveAttachment = (index: number) => {
    setPendingAttachments((prev) => {
      const target = prev[index]
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl)
      return prev.filter((_, i) => i !== index)
    })
  }

  const resetTextareaHeight = () => {
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleSend = () => {
    if (!canSend) return

    const attachments: Attachment[] | undefined =
      pendingAttachments.length > 0
        ? pendingAttachments.map(({ file }) => ({
            name: file.name,
            type: file.type,
            size: file.size,
            file,
          }))
        : undefined

    const message: ChatMessage = {
      id: createMessageId(),
      role: 'user',
      content: text.trim(),
      attachments,
      createdAt: Date.now(),
    }

    onSend(message)

    // Clear the draft immediately — don't wait for the reply to stream in.
    pendingAttachments.forEach((attachment) => {
      if (attachment.previewUrl) URL.revokeObjectURL(attachment.previewUrl)
    })
    setPendingAttachments([])
    setText('')
    resetTextareaHeight()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  const handleTextareaChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    setText(event.target.value)

    const el = event.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`
  }

  return (
    <div className="input-area">
      <div className="input-area-inner">
        {pendingAttachments.length > 0 && (
          <div className="attachment-chip-row">
            {pendingAttachments.map((attachment, index) => (
              <div
                className="attachment-chip"
                key={`${attachment.file.name}-${index}`}
              >
                {attachment.previewUrl ? (
                  <img
                    className="attachment-chip-thumbnail"
                    src={attachment.previewUrl}
                    alt=""
                  />
                ) : (
                  <FileIcon size={16} strokeWidth={1.75} aria-hidden="true" />
                )}
                <span className="attachment-chip-name">
                  {attachment.file.name}
                </span>
                <button
                  type="button"
                  className="attachment-chip-remove"
                  aria-label={`Remove ${attachment.file.name}`}
                  onClick={() => handleRemoveAttachment(index)}
                >
                  <X size={14} strokeWidth={1.75} aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="input-area-row">
          <button
            type="button"
            className="input-attach-button"
            aria-label="Attach files"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
          >
            <Paperclip size={20} strokeWidth={1.75} aria-hidden="true" />
          </button>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="input-file-hidden"
            tabIndex={-1}
            onChange={(event) => {
              handleFilesSelected(event.target.files)
              // Allow re-selecting the same file later (e.g. after removing it).
              event.target.value = ''
            }}
          />

          <textarea
            ref={textareaRef}
            className="input-textarea"
            placeholder="Message Toni…"
            rows={1}
            value={text}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
          />

          <button
            type="button"
            className="input-send-button"
            aria-label="Send message"
            onClick={handleSend}
            disabled={!canSend}
          >
            <ArrowUp size={18} strokeWidth={2} aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default InputArea
