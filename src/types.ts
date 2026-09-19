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
  folderId?: string // undefined for Anne's conversations, and for any not-yet-migrated Toni chat mid-migration
}

export interface Folder {
  id: string
  name: string
  createdAt: number
  collapsed: boolean
}

export interface ChatPageConfig {
  name: string // "Toni" | "Anne" — wordmark, placeholder, mock reply text
  storageKey: string // localStorage key for this page's conversations
  accent: string // e.g. "#c084fc" | "#f472b6"
  accentBg: string // rgba tint derived from accent
  accentBorder: string // rgba tint derived from accent
  emptyStateGreeting: string
  mockReplyText: string
  foldersEnabled?: boolean
  // When set, attachments are uploaded to the real Nemo backend (scanned,
  // turned into follow-up questions) instead of going through the mock
  // reply. Undefined on every page that hasn't been wired up yet (Toni).
  reportIntegration?: { baseUrl: string; token: string }
}

// --- Nemo backend response shapes (see backend/FRONTEND_INTEGRATION.md) ---

export interface Company {
  id: string
  name: string
}

export interface ReportSummary {
  id: string
  company_id: string
  period_start: string
  period_end: string
  scenario: string
  revision: number
  created_at: string
}

export interface ReportRequestSnapshot {
  request_id: string
  company_id: string
  frequency: string
  period_start: string
  period_end: string
  due_date: string
  currency: string
  required_fields: string[]
  arr_applicable: boolean | null
}

export interface AnswerContract {
  type: 'number' | 'text'
  value_required: boolean
  currency_required: boolean
  unit: string | null
  dates_required: Array<'period_start' | 'period_end' | 'as_of_date'>
  definition_required: boolean
  allow_explicit_not_applicable: boolean
  company_message_reference_required: boolean
}

export interface CandidateOption {
  candidate_id: string
  value: number | string | null
  currency: string | null
  unit: string | null
  period_start: string | null
  period_end: string | null
  as_of_date: string | null
  source: unknown
}

export interface ReportQuestion {
  question_id: string
  field: string
  write_path: string
  reason: string
  all_issues: string[]
  question: string
  priority: number
  candidate_options: CandidateOption[]
  answer_contract: AnswerContract
}

export interface QuestionQueue {
  questions: ReportQuestion[]
  remaining: ReportQuestion[]
  total_unresolved_fields: number
}

export interface CompanyReportView {
  id: string
  company_id: string
  period_start: string
  period_end: string
  scenario: string
  revision: number
  latest_submission: unknown
  updates: unknown[]
  documents: Array<{ id: string; filename: string }>
  draft?: unknown
  report?: { request: ReportRequestSnapshot; fields: Record<string, unknown> }
  question_queue?: QuestionQueue
  reviewed_hash?: string
}

export interface UploadResult {
  document_id: string
  job_id?: string
  status?: string
  duplicate?: boolean
  revision: number
}

export interface JobStatus {
  id: string
  document_id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  error: string | null
  report_id: string
  created_at: string
  finished_at: string | null
}

export interface FieldAnswer {
  value?: number | string
  currency?: string
  unit?: string
  period_start?: string
  period_end?: string
  as_of_date?: string
  definition?: string
}

// Answer payload sent to POST /reports/{id}/questions/{qid}/answers — either
// a typed field correction, or `{ not_applicable: true }` (ARR only).
export type QuestionAnswer = FieldAnswer | { not_applicable: true }
