import App from '../App'
import type { ChatPageConfig } from '../types'

// TODO(task 5): replace with the real Anne/pink/statements config.
const config: ChatPageConfig = {
  name: 'Toni',
  storageKey: 'toni:conversations',
  accent: '#c084fc',
  accentBg: 'rgba(192, 132, 252, 0.15)',
  accentBorder: 'rgba(192, 132, 252, 0.5)',
  emptyStateGreeting: 'What can I help you with?',
  mockReplyText:
    "No backend is connected yet — this is a simulated reply from Toni's mock response service. Once a real backend is wired up, responses will stream in through this same interface.",
}

function CompanyChat() {
  return <App config={config} />
}

export default CompanyChat
