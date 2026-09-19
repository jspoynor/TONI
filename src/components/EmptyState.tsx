import './EmptyState.css'

/**
 * Centered greeting shown in the main panel when there is no active
 * conversation (e.g. right after "New Chat" or on first load with no
 * conversations yet). Purely presentational — no props needed.
 */
function EmptyState() {
  return (
    <div className="empty-state">
      <h1 className="empty-state-greeting">What can I help you with?</h1>
    </div>
  )
}

export default EmptyState
