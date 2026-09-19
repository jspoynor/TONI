# Nemo sample kit 01

A fictional healthcare software company's August 2026 reporting packet, designed for local extraction and later conversational AI testing. All company details, financial values and management statements were authored for this demo. They are not TGH portfolio data, real company disclosures, or benchmark estimates.

## Start with these files

1. `uploads/01_complete_monthly.pdf`: four pages: income statement, balance sheet, cash-flow statement, management update. Selectable text.
2. `uploads/02_income_only_missing_context.pdf`: only the income statement. Cash, ARR and management context must come from follow-up answers.
3. `uploads/03_scanned_monthly.pdf`: the complete packet rendered as page images with no text layer. Tests OCR rather than native text extraction. This is a clean synthetic scan, not a noisy camera photo.
4. `uploads/04_ambiguous_conflicting_note.pdf`: upload alongside the complete packet to test conflicting cash and unclear revenue units/period.
5. `uploads/05_wrong_period.txt`: annual 2025 figures that must not populate an August 2026 request.

**Keep developer answer keys out of model inputs.** They are for you and Jackson to evaluate results; uploading them with the source document would invalidate the missing-information tests. Treat cases as separate requests, not one combined folder upload.

## What the complete packet should produce

| Field | Expected value |
|---|---|
| Revenue, August 2026 | USD 120,000 |
| Cash, August 31, 2026 | USD 420,000 |
| ARR, August 31, 2026 | USD 1,200,000, excluding one-time fees |
| Management context | New deployment increased recurring and implementation revenue |
| Risk | Unsigned November renewal covering USD 30,000 MRR |
| Help requested | Two hospital operations introductions; fractional finance lead referral |

These remain unconfirmed until the company reviews them. See developer/expected_complete.json for field-level page references and developer/follow_up_demo.md for the incomplete-packet dialogue.

## Work split

- Jackson: build the upload/chat/report preview against ../reporting/draft.schema.json and ../reporting/examples (the developer fixtures are the earlier contract). The first file upload should produce the draft state, not a submitted report.
- You: test page-text extraction, compare results with the answer keys, and later connect the extraction/follow-up instructions to the OpenAI API.
- Together: confirm field names, source display, missing/conflicting states and the explicit submit action before integration.

## Local extraction

The included developer/extract_local.py makes no network calls and uses no API credits. Install the Python dependency `pypdf`, then run from this kit's directory:

```bash
python developer/extract_local.py uploads/01_complete_monthly.pdf --output complete_text.json
python developer/extract_local.py uploads/03_scanned_monthly.pdf --output scanned_text.json
```

The scanned case additionally requires the system commands `pdftoppm` (Poppler) and `tesseract`, plus English OCR language data. Both native text extraction and Tesseract OCR have now been executed. See ../ocr-demo and ../ocr-test-cases for measured outputs and limitations. Install these commands on your own machine before rerunning scanned inputs.

The starter routes pages with very little embedded text to OCR. This simple heuristic will not detect every damaged text layer or mixed text/image page. Manually review those cases. Tesseract text is not a reliable table parser; preserve page boundaries and check row/column alignment, parentheses, currency and units before relying on numbers. The later AI step still requires an answer-key evaluation and human review.

## Research basis

Reviewed September 19, 2026. These sources informed structure, not the invented financial amounts.

- [TGH Research & Innovation](https://www.tgh.org/research-and-innovation): describes TGH Ventures' interest in emerging healthcare companies. We selected a fictional care-coordination software business to make the demo relevant; this does not assert TGH investment interest in this company or confirm their reporting requirements.
- [Carta: configuring requests for information](https://releasenotes.carta.com/modify-and-request-information-from-portfolio-companies-3da5jO): documents configurable reporting periods, requested files and KPIs, and recommends keeping the KPI set small. This is historical product documentation, not verification of the buyer's current account, UI or import schema. Nemo uses three financial fields plus narrative questions.
- [Underscore VC investor-update template](https://underscore.vc/resources/investor-update-template/): supports concise metrics with context, challenges and actionable asks. Our narrative fields reflect those categories.
- [Tesseract quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html): discusses resolution, skew, segmentation and table-recognition limitations. The OCR helper renders at 300 DPI; clean input does not guarantee accurate financial extraction.

## Checks completed / limitations

- Income statement totals, both balance-sheet totals and August cash movements reconcile.
- August net loss is 56,000; operating cash use is 70,000; total cash decrease is 80,000. These intentionally differ.
- Revenue is 120,000, including 20,000 nonrecurring implementation fees. ARR is explicitly 1,200,000, not 1,440,000.
- Image-only PDF has no embedded text. Complete PDF has four readable text pages.
- This kit includes source documents, fixtures and a local extraction starter. It is not a working Nemo app; no OCR or OpenAI accuracy score is claimed.
