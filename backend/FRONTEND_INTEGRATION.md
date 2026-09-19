# Frontend integration guide for Jackson

Backend setup: [README](README.md). Full API schemas: [openapi.json](openapi.json).

## Connection and authentication

- API base URL: `http://127.0.0.1:8010`
- Interactive docs: `http://127.0.0.1:8010/docs`
- Health check: `GET /health`
- Frontend configuration: `VITE_API_BASE_URL=http://127.0.0.1:8010` in your local `.env.local`.

Localhost works only on the computer running the backend. Run PostgreSQL and the backend locally using the README, or use a separately hosted API. This is not a remote deployment URL.

Open the frontend at `http://localhost:5173`, allowed by default. For `http://127.0.0.1:5173`, start/restart the backend with `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`.

Data endpoints require `Authorization: Bearer <development-token>`. Use the company token for Anne/company actions and the VC token for Toni/VC actions. The demo importer writes a private credentials file; the README explains provisioning. Tokens belong to the database that issued them. Never commit credentials. Keep the OpenAI key in the backend worker, never in the frontend.

## Endpoints

| UI action | Method and endpoint |
|---|---|
| List accessible companies | `GET /companies` |
| Create company (VC) | `POST /companies` |
| List company reports | `GET /companies/{company_id}/reports` |
| Create reporting request (VC) | `POST /companies/{company_id}/reports` |
| Read report and questions | `GET /reports/{report_id}` |
| Upload document (company) | `POST /reports/{report_id}/documents?expected_revision=N` |
| Check scan progress | `GET /jobs/{job_id}` |
| Download original | `GET /documents/{document_id}/download` |
| Answer follow-up (company) | `POST /reports/{report_id}/questions/{question_id}/answers` |
| Correct field (company) | `POST /reports/{report_id}/fields/{field_name}/corrections` |
| Submit reviewed report (company) | `POST /reports/{report_id}/submit` |
| Read submitted history | `GET /reports/{report_id}/versions` |
| Comment below submitted report | `POST /reports/{report_id}/comments` |

## Upload and follow-up flow

1. Fetch accessible companies, then their reporting requests. Use returned IDs.
2. Fetch the company report for its current `revision`, draft, validation results and `question_queue`.
3. Upload multipart form data with a `file` field and the current revision as `expected_revision`. Let the browser set the multipart Content-Type boundary. Supported: PDF or UTF-8 TXT, up to 10 MB and 10 PDF pages. TXT scanning is limited to 45 lines of at most 110 characters each.
4. For a new upload, poll the returned `job_id` until `succeeded` or `failed`, then refresh the report. Duplicate uploads return `duplicate: true` without a new job ID; do not poll an undefined ID.
5. Run the separate worker (`python worker.py`) to process queued scans. Uploading alone queues work; the worker makes paid OpenAI calls. Failed jobs need operator review before retrying.
6. Render returned questions. Send structured answers plus the exact company message and current revision. Refresh after each answer/correction.

There is no general `/chat` endpoint or streaming AI chat endpoint yet. Arbitrary natural-language replies are not automatically interpreted into fields.

Example cash answer/correction body (illustrative values; adapt to the actual question and period):

```json
{
  "expected_revision": 3,
  "message": "Cash was USD 150,000 on August 31.",
  "answer": {
    "value": 150000,
    "currency": "USD",
    "unit": "base_units",
    "as_of_date": "2026-08-31"
  }
}
```

Answer fields depend on the question. See [question bank](question_bank.json) and [answer handling](questions.py).

## Explicit submission

Fetch the latest company report, show the preview/evidence, and wait for the company to click Submit. Send the revision and hash from that reviewed response:

```json
{
  "expected_revision": 4,
  "reviewed_hash": "HASH_FROM_REVIEWED_REPORT",
  "company_confirmed": true
}
```

Do not auto-submit after scanning. Pending/failed scans and unresolved required information block submission. For 409, refresh and review again. For 422, show the API validation detail.

## VC view and later updates

With the VC token, `GET /reports/{report_id}` returns `latest_submission` and `updates`, without the working draft. If `latest_submission` is null, show that no report has been submitted. Otherwise show `latest_submission.snapshot` as the official report, with dated `updates` underneath.

Later uploads, corrections and comments leave the submitted snapshot fixed. Corrections also change the working draft; another explicit submission creates a new official version.

Comment body for an existing submitted report:

```json
{ "body": "The renewal agreement has now been signed." }
```

Render messages/comments as text, not raw HTML. Development authentication, local storage and the worker are prototype infrastructure; production hosting/login and general chat interpretation remain separate work.
