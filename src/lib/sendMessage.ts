import type { Attachment, ChatMessage } from '../types'

const CHUNK_DELAY_MS = 35

const PLACEHOLDER_TEXT =
  "No backend is connected yet — this is a simulated reply from Toni's mock response service. Once a real backend is wired up, responses will stream in through this same interface."

/** Pauses for `ms` milliseconds. Used to simulate network/typing latency between streamed chunks. */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Splits `text` into small streamable pieces (words, each keeping its
 * trailing whitespace) so a caller can render them incrementally and see the
 * reply "type out" rather than appear all at once.
 */
function toChunks(text: string): string[] {
  return text.match(/\S+\s*/g) ?? [text]
}

/**
 * Mock implementation of the backend send seam. Ignores `messages` and
 * `attachments` for the purposes of generating a reply (there is no backend
 * to send them to), but echoes the attachment count back so the attachment
 * plumbing can be verified end-to-end once this is wired into the UI.
 *
 * This is the one module a real fetch/SSE implementation will replace later;
 * callers should only ever import `sendMessage` from here, not reach past it
 * into any lower-level networking code.
 */
export async function* sendMessage(
  messages: ChatMessage[],
  attachments: Attachment[],
): AsyncGenerator<string> {
  void messages

  const text =
    attachments.length > 0
      ? `${PLACEHOLDER_TEXT} (received ${attachments.length} attachment${attachments.length === 1 ? '' : 's'})`
      : PLACEHOLDER_TEXT

  for (const chunk of toChunks(text)) {
    await sleep(CHUNK_DELAY_MS)
    yield chunk
  }
}
