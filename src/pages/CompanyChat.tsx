import App from '../App'
import type { ChatPageConfig } from '../types'

const config: ChatPageConfig = {
  name: 'Anne',
  storageKey: 'anne:conversations',
  accent: '#f472b6',
  accentBg: 'rgba(244, 114, 182, 0.15)',
  accentBorder: 'rgba(244, 114, 182, 0.5)',
  emptyStateGreeting: 'Upload your financial statements to get started',
  mockReplyText:
    "No backend is connected yet — this is a simulated reply from Anne's mock response service. Once a real backend is wired up, you'll be able to upload financial statements and get real answers here.",
}

function CompanyChat() {
  return <App config={config} />
}

export default CompanyChat
