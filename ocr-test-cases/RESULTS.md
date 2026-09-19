# Remaining sample cases: direct extraction versus OCR

Run locally on September 19, 2026 using pypdf and Tesseract 4.1.1. No OpenAI API calls or credits were used.

| Case | Direct extraction | OCR | Selected checks |
|---|---|---|---|
| Income statement only | <0.01 seconds | 1.61 seconds | 2/2 in each mode |
| Complete packet plus conflicting note | 0.01 seconds | 6.93 seconds | 3/3 in each mode |
| Wrong reporting period | <0.01 seconds | 0.72 seconds | 3/3 in each mode |

These are single-run times and fixture-specific text-preservation checks, not whole-document accuracy scores. Each mode passed eight checks across the three remaining scenarios. The earlier complete-packet run and its separate scanned counterpart remain in the sibling `ocr-demo` directory.

## What the checks mean

### Missing information

Both modes retained revenue of 120,000 versus 100,000 and net losses of (56,000) versus (60,000). The upload contains only an income statement. Cash, ARR, management explanation, risks and help requests are not supplied. The expected later behavior is to request them, not infer them. This run did not execute a model or automatically determine semantic completeness.

[Direct text](missing_direct.txt) | [OCR text](missing_ocr.txt)

### Conflicting / ambiguous information

Both modes preserved cash of 420,000 in the balance sheet and 450,000 in the supplemental note. They also retained `Revenue: 120` exactly, without converting it to 120,000. The future interpreter should preserve these candidate values and ask for the correct cash amount and the note's currency, revenue units and measurement period. These are reviewer observations against the test specification, not generated follow-up results.

[Direct text](conflict_direct.txt) | [OCR text](conflict_ocr.txt)

### Wrong reporting period

Both modes retained the explicit year ended December 31, 2025, annual revenue of 900,000 and cash of 800,000 at December 31, 2025. Those figures should not populate the requested August 2026 form. The expected next action is to request the correct period, not divide annual revenue by 12.

[Direct text](wrong_period_direct.txt) | [OCR text](wrong_period_ocr.txt)

## How the two formats were tested

- PDFs: read the original embedded text, then separately render the same PDF pages to 300-DPI images and force Tesseract to recognize them.
- TXT: read the source text directly, then render the exact text into a 300-DPI page image for OCR.
- These are controlled synthetic scan tests, not real camera captures. The earlier complete scan used a 160-DPI source image; these new renders begin at 300 DPI, so header errors can differ.
- OCR still corrupted the colored `Line item` table header into `Taman)`. The financial figures and dates selected for this run's checks survived. No errors were silently repaired.
- Page numbers and original filenames are retained in each JSON output. Image intermediates are in `work/ocr-test-cases`.

## Next step and API cost

Local code can validate missing required fields in an already structured draft, check explicit date ranges, compare numeric candidates, and present fixed questions without paid API calls. It does not automatically understand arbitrary financial documents or management explanations.

For the planned OpenAI interpreter, connect a funded OpenAI API project. That stage will turn page-tagged text into candidate fields, interpret existing narrative, flag uncertainty and draft context-sensitive follow-up questions. All values still require validation and company review. Sending extracted text does not require paying for another OCR service.

## Reproduce

Install the repository's Python requirements, Poppler, Tesseract English data and a DejaVuSans font (or set NEMO_OCR_FONT). Run from the repository root:

```bash
python ocr-test-cases/run_cases.py
```

It regenerates the JSON/text outputs and comparison.json. This narrative report records the original run and does not update its timing table automatically.
