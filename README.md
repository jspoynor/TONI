# TONI — Nemo reporting prototype

Nemo helps portfolio companies turn financial documents and a short conversation into a confirmed investor update. The intended buyer is TGH Ventures; the proposed workflow is informed by its use of Carta, not a verified Carta integration.

## Current status

- **Sample data:** one fictional healthcare software company, CareFlow, represented by five source files/test scenarios. These are synthetic data, not real portfolio disclosures. The complete PDF and scanned PDF contain the same report.
- **Local extraction implemented:** selectable PDF/TXT extraction with pypdf and image-only PDF OCR with Poppler + Tesseract. Complete, missing-information, conflicting-note and wrong-period scenarios have been exercised in direct-text and OCR formats.
- **Rules implemented:** six reporting fields, source evidence, missing/unclear/conflicting states, period/currency/unit checks, at most three questions, explicit confirmation and a detached submitted snapshot. Monthly/quarterly requests carry explicit boundaries supplied by the app.
- **Validation:** 22 local rules tests pass. These tests use hand-authored structured fixtures, not automatically interpreted OCR output. OCR spot checks preserved selected financial figures, but some date headers were garbled; no overall accuracy score is claimed.
- **Next:** OpenAI interpretation, an independent visual reading, comparison of the two readings, and conversational answer updates. No OpenAI API call or dual-reader accuracy test has run yet. UI integration, persistent storage and scheduled requests are also pending in this data/backend work.

## Work split

Jackson owns the company upload/chat/report-preview UI (hours 3–5), initially using fixtures with no live API. The project owner and Codex own sample data, local extraction, reporting rules, and the upcoming OpenAI adapter. This README describes the data/backend work on main; it does not assess Jackson's other branches.

## Files

| Folder | Contents |
|---|---|
| [sample-data](sample-data/START_HERE.md) | Five upload documents, original answer keys and local extractor |
| [ocr-demo](ocr-demo/README.md) | Complete report: direct text versus image-only OCR results |
| [ocr-test-cases](ocr-test-cases/RESULTS.md) | Remaining scenarios, saved outputs and rerun script |
| [reporting](reporting/README.md) | Current schema, rules engine, tests and example drafts/reports |

Do not send developer answer keys to the model. Each test scenario is a separate reporting request; the conflicting note is intentionally paired with the complete packet.

## Run locally

Python 3.10+ is required. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s reporting -v
python reporting/reporting.py reporting/examples/missing_input.json --output missing_result.json
python sample-data/developer/extract_local.py sample-data/uploads/01_complete_monthly.pdf --output complete_text.json
```

For scanned files, install Poppler (`pdftoppm`), Tesseract and English language data. On macOS with Homebrew: `brew install poppler tesseract`. On Ubuntu: `sudo apt install poppler-utils tesseract-ocr tesseract-ocr-eng fonts-dejavu-core`.

```bash
bash ocr-demo/run_again.sh
python ocr-test-cases/run_cases.py
python reporting/build_examples.py
```

The remaining-case script renders text/PDF inputs to images for its second local pass; it uses DejaVuSans.ttf. Set `NEMO_OCR_FONT` to a TrueType font path if unavailable. Generated page images go in ignored `work/`. Timings vary by machine. The complete-case launcher only refreshes its page JSON, not historical timing/text summaries.

## Reporting contract and follow-ups

Collect revenue for the requested period, cash on hand as of period end, ARR when applicable (with its definition), management context, risks, and requests for help. The VC selects monthly or quarterly frequency, explicit period boundaries, due date and required fields per company. Recurring scheduling is future work.

The target two-reading flow is:

1. Extract local page text with pypdf/Tesseract and interpret it into sourced candidates.
2. Separately ask an OpenAI vision-capable model to read the original document/page images, without seeing the first reading or answer keys.
3. Compare values, units, currency and dates; preserve both sources. Missing information, uncertainty or disagreement triggers company follow-up instead of silently choosing a result.
4. Ask for explanations, risks and help needed; a numerical match does not supply management context.
5. Show the draft and evidence for explicit company confirmation before submission.

The current extractor chooses embedded text or OCR per page; it does **not** yet run this two-reader flow. Two readers agreeing will not prove correctness. The rules layer validates structured evidence but cannot recover meaning directly from raw OCR or authenticate the submitting user.

## API setup (next step)

Fund the OpenAI API through [API billing](https://platform.openai.com/settings/organization/billing/overview). API billing is separate from ChatGPT/Codex subscription credits. Keep the future `OPENAI_API_KEY` in a local ignored `.env` or environment variable; never place it in frontend code, chat or Git. Tesseract itself uses no paid API credits. No key is needed for the code currently committed here.

[12-hour build plan](https://app.notion.com/p/3e08ff972e4781739613f7efef7a3ab8)
