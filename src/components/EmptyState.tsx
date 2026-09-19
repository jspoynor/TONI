import './EmptyState.css'

export interface EmptyStateProps {
  greeting: string
}

/**
 * Centered greeting shown in the main panel when there is no active
 * conversation (e.g. right after "New Chat" or on first load with no
 * conversations yet). Purely presentational.
 */
function EmptyState({ greeting }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <h1 className="empty-state-greeting">{greeting}</h1>
    </div>
  )
}

export default EmptyState
