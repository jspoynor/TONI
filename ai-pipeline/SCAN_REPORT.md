# OpenAI and local extraction comparison

Synthetic CareFlow samples only. Model: `gpt-4.1-mini-2025-04-14`. Each document used two isolated requests: saved local text and rendered original page images. Both interpretation requests used the same model; this is independence of inputs, not independent model families. Answer keys were used only below for evaluation, never in scan requests.

## Final-run comparison

| Case | Revenue | Cash | ARR | Management | Risks | Help | Draft |
|---|---|---|---|---|---|---|---|
| complete | disagreement | disagreement | disagreement | match | match | match | needs_information |
| scanned | disagreement | disagreement | disagreement | match | match | match | needs_information |
| missing | disagreement | both_missing | both_missing | both_missing | both_missing | both_missing | needs_information |
| conflict | match | match | disagreement | disagreement | disagreement | disagreement | needs_information |
| wrong_period | match | match | both_missing | both_missing | both_missing | both_missing | needs_information |

## Check against the manually authored baseline

These checks compare amount sets only. Field validation separately checks currency, units, dates, definition and evidence uncertainty. They are a small fixture evaluation, not a general OCR accuracy score.

30/30 amount-set checks matched the baseline.

## complete: form and follow-ups

| Field | Accepted draft value | Status |
|---|---|---|
| revenue | Not accepted / not provided | conflicting |
| cash_on_hand | Not accepted / not provided | conflicting |
| arr | Not accepted / not provided | conflicting |
| management_context | Revenue rose from USD 100,000 in July to USD 120,000 in August. A new hospital deployment added USD 10,000 of recurring subscription revenue and an additional USD 10,000 of one-time implementation revenue compared with July. The deployment went live August 1. | ready |
| risks | One customer representing USD 30,000 of live MRR renews in November 2026. The renewal is not signed. The account lead will present a renewal proposal by October 1; we are not assuming churn has occurred. | ready |
| help_requested | Please introduce us to two hospital operations leaders for discovery calls and recommend a fractional finance lead. | ready |
- **revenue (units):** Is the revenue shown in whole currency units, thousands or millions? Please provide the amount in whole units.
- **cash_on_hand (units):** Is the cash balance shown in whole currency units, thousands or millions? Please provide the amount in whole units.
- **arr (units):** Is the ARR shown in whole currency units, thousands or millions? Please provide the amount in whole units.
- Reader warnings: Review table alignment, negative signs, dates, currencies and units. Text length does not prove accuracy; mixed text/image pages can require manual OCR.; Revenue and ARR currency and units are stated as USD and whole dollars, but units (e.g., thousands) are not explicitly stated, assumed base units.; Cash on hand dates are as of month-end, consistent with balance sheet dates.; No explicit ARR dates other than as of August 31, 2026.; No explicit total revenue definition beyond sum of subscription and implementation revenue.
- Validation issues: `{"revenue": ["conflicting_candidates"], "cash_on_hand": ["conflicting_candidates"], "arr": ["conflicting_candidates"]}`

## scanned: form and follow-ups

| Field | Accepted draft value | Status |
|---|---|---|
| revenue | Not accepted / not provided | conflicting |
| cash_on_hand | Not accepted / not provided | conflicting |
| arr | Not accepted / not provided | conflicting |
| management_context | Revenue rose from USD 100,000 in July to USD 120,000 in August. A new hospital deployment added USD 10,000 of recurring subscription revenue and an additional USD 10,000 of one-time implementation revenue compared with July. The deployment went live August 1. | ready |
| risks | One customer representing USD 30,000 of live MRR renews in November 2026. The renewal is not signed. The account lead will present a renewal proposal by October 1; we are not assuming churn has occurred. | ready |
| help_requested | Please introduce us to two hospital operations leaders for discovery calls and recommend a fractional finance lead. | ready |
- **revenue (units):** Is the revenue shown in whole currency units, thousands or millions? Please provide the amount in whole units.
- **cash_on_hand (units):** Is the cash balance shown in whole currency units, thousands or millions? Please provide the amount in whole units.
- **arr (units):** Is the ARR shown in whole currency units, thousands or millions? Please provide the amount in whole units.
- Reader warnings: Review table alignment, negative signs, dates, currencies and units. Text length does not prove accuracy; mixed text/image pages can require manual OCR.; Revenue and cash amounts have clear currency USD and whole dollar units but no explicit unit scaling stated.; ARR is reported only as a management figure with a definition, no period start/end but as_of_date August 31, 2026.
- Validation issues: `{"revenue": ["conflicting_candidates"], "cash_on_hand": ["conflicting_candidates"], "arr": ["conflicting_candidates"]}`

## missing: form and follow-ups

| Field | Accepted draft value | Status |
|---|---|---|
| revenue | Not accepted / not provided | conflicting |
| cash_on_hand | Not accepted / not provided | missing |
| arr | Not accepted / not provided | missing |
| management_context | Not accepted / not provided | missing |
| risks | Not accepted / not provided | missing |
| help_requested | Not accepted / not provided | missing |
- **revenue (units):** Is the revenue shown in whole currency units, thousands or millions? Please provide the amount in whole units.
- **cash_on_hand (missing):** What was your cash balance as of 2026-08-31, in USD? Please state whether restricted cash is included.
- **arr (missing):** What was your ARR as of 2026-08-31, in USD, and what does it include or exclude? If ARR does not apply to your business, please say so.
- 3 additional questions stay queued; maximum three shown at once.
- Reader warnings: No cash on hand or ARR data present in document.; Revenue periods are monthly, not annual or quarterly, which may be insufficient context for some uses.
- Validation issues: `{"revenue": ["conflicting_candidates"], "cash_on_hand": ["missing"], "arr": ["missing"], "management_context": ["missing"], "risks": ["missing"], "help_requested": ["missing"]}`

## conflict: form and follow-ups

| Field | Accepted draft value | Status |
|---|---|---|
| revenue | Not accepted / not provided | conflicting |
| cash_on_hand | Not accepted / not provided | conflicting |
| arr | Not accepted / not provided | conflicting |
| management_context | Not accepted / not provided | conflicting |
| risks | Not accepted / not provided | conflicting |
| help_requested | Not accepted / not provided | conflicting |
- **revenue (conflict):** The attached readings give different information for revenue. Please review the values and sources shown and tell us which is correct, or provide a correction. Include currency, units and the relevant dates.
- **cash_on_hand (conflict):** The attached readings give different information for cash balance. Please review the values and sources shown and tell us which is correct, or provide a correction. Include currency, units and the relevant dates.
- **management_context (conflict):** The attached readings give different information for management explanation. Please review the values and sources shown and tell us which is correct, or provide a correction. Please give the explanation you want included in this report.
- 3 additional questions stay queued; maximum three shown at once.
- Reader warnings: This note does not specify currency, revenue units, or the revenue measurement period.; Revenue amount 120 has no specified currency, units, or measurement period.
- Validation issues: `{"revenue": ["conflicting_candidates"], "cash_on_hand": ["conflicting_candidates"], "arr": ["conflicting_candidates"], "management_context": ["conflicting_candidates"], "risks": ["conflicting_candidates"], "help_requested": ["conflicting_candidates"]}`

## wrong_period: form and follow-ups

| Field | Accepted draft value | Status |
|---|---|---|
| revenue | Not accepted / not provided | needs_clarification |
| cash_on_hand | Not accepted / not provided | needs_clarification |
| arr | Not accepted / not provided | missing |
| management_context | Not accepted / not provided | missing |
| risks | Not accepted / not provided | missing |
| help_requested | Not accepted / not provided | missing |
- **revenue (period):** The available revenue does not clearly match this request. Please provide information for 2026-08-01 through 2026-08-31.
- **cash_on_hand (period):** The available cash balance does not clearly match this request. Please provide the value as of 2026-08-31.
- **arr (missing):** What was your ARR as of 2026-08-31, in USD, and what does it include or exclude? If ARR does not apply to your business, please say so.
- 3 additional questions stay queued; maximum three shown at once.
- Reader warnings: Document states: This document contains no August 2026 financial results.; Document states no August 2026 financial results but is dated for year ended December 31, 2025
- Validation issues: `{"revenue": ["reporting_period_missing_or_wrong"], "cash_on_hand": ["as_of_date_missing_or_wrong"], "arr": ["missing"], "management_context": ["missing"], "risks": ["missing"], "help_requested": ["missing"]}`

## Simulated answer round trip

In the missing case, a labeled simulated company answer fills cash at USD 420,000 as of August 31. Only the cash field changes; other unanswered fields remain queued. The report remains unconfirmed. See `results/simulated_follow_up.json`. This demonstration uses a structured answer, not a live natural-language answer interpreter.

## Usage and limitations

32 paid API responses across all three development runs. Estimated total: **USD 0.096919**. Calculated from returned token usage at $0.40/M uncached input, $0.10/M cached input and $1.60/M output; this is an estimate, not a billing receipt. Model pricing checked September 19, 2026: https://developers.openai.com/api/docs/models/gpt-4.1-mini

The first run caught blank narrative values and conservative date/quote issues. The second run also demonstrated shared omissions: both readings skipped the ambiguous note and annual figures. The final per-document extraction removed the target request from model input and recovered those amounts; missing units and other differences still require follow-up. Its original responses are retained in `results_initial`. The revised schema requires nonempty narrative values. The adapter normalizes whitespace and hyphen line wraps, removes redundant ARR “defined as” framing, and ignores numeric-only metadata slots on narrative fields while retaining raw model responses. It does not use expected answers to repair output.

The sample PDFs are clean synthetic documents. Visual evidence citations still require human review; text substring checks cannot prove that a number or date is interpreted correctly. Two readings may share errors. This is a field-extraction comparison, not a full verbatim OCR accuracy test. Production identity checks, UI wiring, persistent audit storage, recurring scheduling and live conversational answer interpretation remain future work. No report has been submitted.
