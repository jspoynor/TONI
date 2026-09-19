import type {
  Company,
  CompanyReportView,
  JobStatus,
  QuestionAnswer,
  QuestionQueue,
  ReportSummary,
  UploadResult,
} from '../types'

export interface ApiConfig {
  baseUrl: string
  token: string
}

/**
 * Thrown for any non-2xx response. `detail` is FastAPI's `{"detail": ...}`
 * body when present, otherwise the raw response text.
 */
export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(`Nemo API error ${status}: ${detail}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(
  config: ApiConfig,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${config.baseUrl}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${config.token}`,
      ...init.headers,
    },
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as { detail?: string }
      if (body?.detail) detail = body.detail
    } catch {
      // Response body wasn't JSON (or was empty) — fall back to statusText.
    }
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

function jsonInit(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export function getCompanies(config: ApiConfig): Promise<Company[]> {
  return request(config, '/companies')
}

export function getCompanyReports(
  config: ApiConfig,
  companyId: string,
): Promise<ReportSummary[]> {
  return request(config, `/companies/${companyId}/reports`)
}

export function getReport(
  config: ApiConfig,
  reportId: string,
): Promise<CompanyReportView> {
  return request(config, `/reports/${reportId}`)
}

export async function uploadDocument(
  config: ApiConfig,
  reportId: string,
  file: File,
  expectedRevision: number,
): Promise<UploadResult> {
  const formData = new FormData()
  formData.append('file', file)

  return request(
    config,
    `/reports/${reportId}/documents?expected_revision=${expectedRevision}`,
    { method: 'POST', body: formData },
  )
}

export function getJob(config: ApiConfig, jobId: string): Promise<JobStatus> {
  return request(config, `/jobs/${jobId}`)
}

export function answerQuestion(
  config: ApiConfig,
  reportId: string,
  questionId: string,
  answer: QuestionAnswer,
  message: string,
  expectedRevision: number,
): Promise<{ revision: number; report: unknown; question_queue: QuestionQueue }> {
  return request(
    config,
    `/reports/${reportId}/questions/${questionId}/answers`,
    jsonInit({ expected_revision: expectedRevision, answer, message }),
  )
}

const POLL_INTERVAL_MS = 3000
const POLL_MAX_ATTEMPTS = 40 // ~2 minutes total

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Polls a scan job until it settles (`succeeded`/`failed`) or gives up after
 * ~2 minutes, returning `null` on timeout. The worker that actually performs
 * scans (`backend/worker.py`) runs separately from the API and may not be
 * running yet — a timeout doesn't mean the job failed, just that the caller
 * should stop waiting and narrate that instead of polling forever.
 */
export async function pollJob(
  config: ApiConfig,
  jobId: string,
): Promise<JobStatus | null> {
  for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt++) {
    const job = await getJob(config, jobId)
    if (job.status === 'succeeded' || job.status === 'failed') return job
    await sleep(POLL_INTERVAL_MS)
  }
  return null
}
