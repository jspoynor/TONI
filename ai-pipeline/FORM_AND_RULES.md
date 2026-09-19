# Nemo reporting form and follow-up rules

This is a draft company investor update. The VC chooses the frequency, date range, due date and required fields. The company reviews all accepted values before submitting. Monthly and quarterly requests use explicit boundaries; scheduling is separate.

| Field | Form input | Evidence / validation | Missing question |
|---|---|---|---|
| revenue | Amount, currency, units, period start/end | Total revenue for the requested period, not ARR or only subscription revenue | What was revenue for this period, in the requested currency? |
| cash_on_hand | Amount, currency, units, as-of date | Cash balance at period end, not cash-flow movement | What was cash at period end? Is restricted cash included? |
| arr | Amount, currency, units, as-of date, definition; applicability | Explicitly reported ARR with definition; never revenue × 12 | What was ARR, and what does it include/exclude? Or is it not applicable? |
| management_context | Company explanation, reporting period | Preserve the source explanation; never infer the reason from a trend | What changed, why, and which changes were recurring or one-time? |
| risks | Risks, mitigation, reporting period | An explicit “none” is valid; absence is not “none” | What risks, actions, owners and timing should the VC know? |
| help_requested | Requested help, reporting period | Preserve the specific ask; explicit “none” is valid | What investor action or introduction is needed, and by when? |

`blank_form.json` is a UI example. `reading.schema.json` is the model output contract. `reporting.Draft` is the validation contract. `results/*_filled_form.json` are actual populated views, not hand-entered expected answers. The current engine stores narrative context as text; details such as risk owner/timing are requested but are not separately required structured fields.

## Processing rules

1. Extract each uploaded document separately. The document reader sees no target reporting period and no answer keys. This prevents it from silently discarding an annual statement or a less-clear draft note.
2. Preserve each raw response with its document, page, quote, reader, metadata evidence and uncertainty. Never take instructions from uploaded content.
3. Code selects matching dates when present and keeps undated evidence. If no matching date exists, retain out-of-period figures so they are flagged. Original responses retain historical comparison-column evidence.
4. Normalize only explicit thousands/millions to whole units. Normalize whitespace and hyphen line wrapping. Ignore numeric-only metadata slots attached to narrative text. Remove redundant ARR “ARR is …, defined as” framing; preserve the definition/exclusions and raw response. No guessed currency, dates or scaling.
5. Compare both readers. Differing values, dates, currencies, units or definitions require review. A candidate present in only one reading is uncertain. Agreement does not imply source completeness or accuracy.
6. Validate required fields, scope, dates, types, units, currency, ARR definition and source uncertainty. A missing or invalid value stays null in the accepted form. Do not choose one conflicting candidate automatically.
7. Ask at most three questions per turn: conflicts first, then uncertainty/metadata, missing numbers, then narrative gaps. Keep the full queue available. Both readings can detect the same document conflict: “match” means they agree on the candidate set, not that those candidates are consistent.
8. Ask about management context even when all numbers match. Never fabricate a causal explanation.
9. Resolve a field only from an explicit company answer or reviewed correction. Preserve original candidates and attach the answering message. Revalidate and advance the question queue.
10. A report remains a draft until explicit company review and submission. The surrounding app must authenticate the user and persist snapshots. Neither model nor answer mapping submits automatically.

## Question-to-field mapping

`question_bank.json` contains field-specific templates for missing data, conflict, one-reader-only evidence, unreadability, period, currency, units, and ARR definition. These are sample questions, not an autonomous model conversation.

Each generated question has:
- `question_id`: includes field, reason and a hash of the current request/evidence.
- `field` and `write_path`: e.g. `cash_on_hand` → `fields.cash_on_hand`.
- `all_issues`: all unresolved validation issues; one focused question is selected first.
- `candidate_options`: values, dates and source references to display alongside the question.
- `answer_contract`: required type, dates, currency and definition.

`questions.apply_answer` accepts a structured answer bound to the current question and a company message reference. It rejects stale questions and unknown properties, changes only the addressed field (or explicit ARR applicability), preserves prior evidence, and revalidates. Free-text answer interpretation into this contract still needs an adapter; do not claim this function understands arbitrary chat.

Example company answer payload (illustrative, not a live submission):

```json
{
  "field": "cash_on_hand",
  "value": 420000,
  "currency": "USD",
  "unit": "base_units",
  "as_of_date": "2026-08-31",
  "message_id": "company-message-123",
  "quote": "Our cash was USD 420,000 as of August 31, 2026."
}
```

Pass only the typed field value/metadata to `apply_answer`; the question selects the destination field, and the message ID/quote are separate required arguments. The UI must not accept an arbitrary destination path supplied by the model.
