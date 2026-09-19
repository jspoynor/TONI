# Local OCR demonstration: measured results

We ran two versions of the same fictional four-page financial packet locally on this machine. No OpenAI or other document-processing service was called.

| Input | Method | Measured time |
|---|---|---|
| Selectable-text PDF | pypdf text extraction | 0.01 seconds |
| Image-only PDF | Poppler rendering at 300 DPI, then Tesseract 4.1.1 English OCR | 6.18 seconds |

These timings are from one run on this machine, not a general speed guarantee. The sample scan was originally rendered at 160 DPI. Resampling it to 300 DPI does not recreate lost detail.

## Inspect the results

- `native_text.txt`: text recovered directly from the selectable-text PDF.
- `ocr_text.txt`: actual OCR output, including mistakes. Nothing has been silently corrected.
- `native_pages.json` and `ocr_pages.json`: page-numbered text suitable as inputs to a later extraction model.
- `spot_checks.json`: expected versus recognized values for eight selected financial rows, and a check for the ARR amount.
- `run_metrics.json`: timings and output sizes.

## What worked

All eight selected rows matched their expected figures, including parentheses for losses/outflows. Revenue, cash and the explicit ARR text survived OCR. Management's risk and help-request text was also visible in the output. This is a limited spot check, not a full accuracy score.

## What did not work

Several colored table headers were garbled. On page 1, `Aug 2026` became `PGT wy.)`. Page 2 lost part of its date header. This can lead to assigning a correct number to the wrong period. Other text on these pages preserves the dates, but an application must check the evidence rather than assume a column's meaning.

OCR gives us text; it has not filled a validated reporting form. The next stage will use the document evidence and reporting request to identify fields, flag uncertainty and generate follow-up questions. No OpenAI stage has run yet.

## Run it again

Install the dependencies in the repository README, then run `bash ocr-demo/run_again.sh` from the repository root. Set `NEMO_PYTHON` if a different Python executable is needed. This updates `ocr_pages.json` only; the other exports and timing summaries describe the original demonstration run.

The original experiment used Tesseract and English data unpacked from Ubuntu Jammy packages into a project-local runtime. These binaries are not committed. The portable launcher uses Tesseract and Poppler installed on your machine.

The documents were processed locally. Network access was used only to download software packages. No API credits were used.
