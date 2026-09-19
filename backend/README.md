# Nemo database and FastAPI backend

One VC manages many companies. Each company owns reporting requests, documents and conversations. This prototype stores scan evidence in PostgreSQL, accepts additional uploads, queues scans, maps structured answers to fields, and saves explicitly submitted versions.

**Submitted reports stay fixed. Later comments, corrections and uploads appear below the submitted report as dated updates.** Corrections also change the working draft. A new explicit submission creates version 2, 3, etc.; it never edits version 1. Neither importing scan data nor running a scan submits a report.

## What is implemented

- PostgreSQL schema (`schema.sql`, initial schema version 1) with one VC enforced by a singleton key. `companies.vc_id` is one-to-many; there is no investor/company membership join table.
- Five saved scan scenarios imported without additional AI calls: one synthetic CareFlow company, five isolated demo requests, six document records, 12 extraction runs and 48 field candidates. Demo scenario labels allow the same period to be tested five ways; live requests are unique per company/period.
- Company/VC bearer-token access with company isolation. Tokens are random, stored hashed in the database and issued by a local operator command. This is a development authentication implementation, not Supabase Auth integration.
- New PDF/TXT uploads stored under generated IDs, with size/type checks, content hashes, duplicate detection, and a persistent scan queue.
- A separate worker runs the existing local-text/visual OpenAI readers and appends evidence. New evidence invalidates old review/selection for affected fields. A company-name mismatch stops the scan for operator review rather than mixing companies.
- Typed corrections and field-bound question answers preserve old evidence and revalidate the draft.
- Explicit submission checks confirmation, current revision/hash, unresolved fields, and unfinished/failed scans. PostgreSQL triggers reject updates/deletes to submitted snapshots and below-report updates.
- VC report responses expose the latest submitted snapshot and the updates feed, not unsubmitted draft values. Company responses include the editable draft, question queue and review hash.

## Database tables

| Table | Purpose |
|---|---|
| vc / companies | One VC and its portfolio companies/settings |
| actors | Scoped development credentials and display names |
| report_requests | Request settings snapshot, period, current draft and revision |
| documents / scan_jobs | Immutable file records and durable processing status |
| extraction_runs | Reader/model output, usage and evidence provenance |
| field_candidates / report_fields | Preserved candidates and current validated field views |
| questions / messages | Question-to-field mapping, question history and company answers |
| report_versions | Immutable explicitly submitted snapshots |
| report_updates | Append-only comments, corrections, uploads and scan updates below a submitted report |
| import_batches | Idempotent import identities and checksums |

`Numeric(24,6)` stores structured financial amounts in candidate rows. Raw source/AI JSON is preserved separately. Company API access is enforced in backend queries; this schema does not install Supabase RLS policies. Do not expose these tables through a public direct-to-database client without separately implementing RLS.

## Run locally

Python 3.10+, PostgreSQL, Poppler, Tesseract English data and DejaVuSans are needed for the full scan path. Core API/import/tests do not call OpenAI. From `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/nemo'
export NEMO_STORAGE="$PWD/storage"
python manage.py init
```

The current schema is created by `db.init` and can also be inspected in `schema.sql`. It is the initial migration, not an automatic upgrade engine for future schema changes. A schema change needs a reviewed migration.

The complete tested scan package is committed as `ai-pipeline/nemo-ai-pipeline.zip`. Extract it locally first:

```bash
unzip ../ai-pipeline/nemo-ai-pipeline.zip -d ../ai-pipeline
python import_scans.py ../ai-pipeline/nemo-ai-pipeline --storage "$NEMO_STORAGE" --credentials demo-credentials.json
uvicorn app:app --host 127.0.0.1 --port 8010
```

`demo-credentials.json` contains a VC token and a CareFlow company token. Keep it private. The importer creates it only if absent and does not print tokens. The `.gitignore` excludes credentials, storage and keys. Open `http://127.0.0.1:8010/docs`, choose Authorize, and use the appropriate bearer token. The importer refuses changed input for an existing import identity instead of overwriting later user edits.

For new companies, the VC uses `POST /companies`, then creates a reporting request. Provision that company's development account locally:

```bash
python manage.py actor --name 'Company finance user' --role company --company-id COMPANY_ID --output company-credentials.json
```

Start the worker separately when paid scanning is wanted:

```bash
export OPENAI_ENV_FILE='/absolute/path/to/private/.env'
python worker.py
# Or process at most one queued job:
python worker.py --once
```

The worker makes two model requests per new document and records returned usage. Uploading alone only queues work. It does not automatically spend credits until a worker is running. Failed jobs do not automatically retry. After investigating a failed job, an operator can use `python manage.py retry-job JOB_ID --acknowledge-possible-charge`. If a worker crashes while a job is running, investigate that job before manually recovering it; no automatic stale-job retry is implemented.

## API for Jackson

| Method / route | Role and behavior |
|---|---|
| GET /companies | VC: all companies; company: itself |
| POST /companies | VC creates a company |
| POST /companies/{id}/reports | VC creates a period request |
| GET /companies/{id}/reports | Scoped request list |
| GET /reports/{id} | Company draft + questions; VC submitted version + updates |
| POST /reports/{id}/documents?expected_revision=N | Company uploads PDF/TXT and queues processing |
| GET /jobs/{id} | Scoped scan status |
| GET /documents/{id}/download | Authorized original-file download |
| POST /reports/{id}/questions/{question_id}/answers | Typed answer + exact company message + expected_revision |
| POST /reports/{id}/fields/{name}/corrections | Company correction to any supported field; retains old evidence |
| POST /reports/{id}/submit | Company confirmation + current revision + reviewed_hash |
| GET /reports/{id}/versions | Submitted history |
| POST /reports/{id}/comments | Company/VC comment below an existing submission |

Render `latest_submission.snapshot` as the official report, with `updates` underneath. Each update has author, time, kind, linked version and optional document. Label corrections as updates to the draft until a new report version is submitted. Render comment text as text, not raw HTML.

Before submitting, refresh the company report, display its full preview and evidence, and send the returned `revision` and `reviewed_hash` only after the company clicks **Submit**. A 409 means refresh/review again; a 422 means the draft/confirmation is invalid. Pending/failed upload jobs block submission.

## Validation and boundaries

13 lifecycle tests passed against isolated PostgreSQL schemas, including import idempotency, company isolation, immutable snapshots, updates below reports, stale review, duplicate uploads, queue completion/failure, and correction/resubmission. `LIVE_SMOKE_RESULT.json` records the additional real upload/worker/OpenAI check. Prior scan/rule tests remain in the scan archive.

```bash
# SQLite for isolated offline API tests:
python -m unittest test_backend -v
# PostgreSQL: this creates/drops only randomly named test_* schemas in the supplied database.
export NEMO_TEST_DATABASE_URL="$DATABASE_URL"
export SCAN_DATA_DIR='../ai-pipeline/nemo-ai-pipeline'
python -m unittest test_backend -v
```

This is a local development backend. Supabase hosting/auth, a production file-storage service, scheduled reporting, notifications and Jackson's actual UI wiring are not deployed. Typed answer handling works; arbitrary natural-language answer interpretation is still separate work. Files are limited to 10 MB and 10 PDF pages; TXT scanning uses a deliberately bounded one-page layout. Do not deploy the local filesystem/auth setup as a finished public service.
