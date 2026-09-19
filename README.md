# TONI — Nemo reporting prototype

Nemo turns portfolio-company financial documents and follow-up answers into reviewed investor updates. Current scope: **one VC managing multiple companies**.

## Current implementation

- [Sample data](sample-data/START_HERE.md): one fictional CareFlow company and five test scenarios; no real portfolio data.
- [Local OCR](ocr-demo/README.md) and [additional test cases](ocr-test-cases/RESULTS.md): saved local extraction results.
- [OpenAI scan results](ai-pipeline/SCAN_REPORT.md): separate local-text and visual readings; 30/30 amount-set checks matched in the final five-case experiment. Units and other metadata still need clarification; this is not a general accuracy guarantee.
- [Complete scan code, inputs and evidence archive](ai-pipeline/nemo-ai-pipeline.zip): reproducible pipeline, field form, question bank and preserved development runs. Extract it before running imports/tests.
- [Database and FastAPI backend](backend/README.md): PostgreSQL schema, idempotent JSON import, scoped company/VC APIs, upload queue/worker, corrections, explicit submission and below-report updates.

## Submitted reports and later updates

A company reviews its draft and clicks **Submit** to create a fixed report version. Later comments, corrections and uploads appear below that report in the VC view with author/time information. New documents and corrections update a separate working draft. The original submitted version stays unchanged; another explicit submission creates a new version.

## Work split

Jackson owns the frontend. The backend exposes the API contract in [backend/openapi.json](backend/openapi.json), with routes and setup instructions in [backend/README.md](backend/README.md). The company interface reads drafts/questions; the VC view reads submitted snapshots and the updates feed.

## Validation and remaining integration

The local PostgreSQL import contains five isolated demo reports, six document records, twelve extraction runs and 48 field candidates. None was auto-submitted. Thirteen PostgreSQL lifecycle tests passed. A real upload/worker/OpenAI smoke test completed successfully in an isolated test schema and left the submitted snapshot unchanged; see [test result](backend/LIVE_SMOKE_RESULT.json).

The backend runs locally. Supabase hosting/auth, production file storage, scheduling and Jackson's UI wiring are not deployed. Development bearer credentials are issued locally and stored hashed. Arbitrary free-text answer interpretation remains separate work; typed field answers and corrections are implemented.

Keep `.env`, credentials, local storage and database files out of Git. The sample archives contain no API keys. See the [Notion build plan](https://app.notion.com/p/3e08ff972e4781739613f7efef7a3ab8) for the original prototype scope.
