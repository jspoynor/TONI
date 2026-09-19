# Reporting rules: actual demo outputs

These are deterministic rules applied to hand-authored structured fixtures. No OpenAI calls and no automatic OCR interpretation.

## Complete

State: **ready_for_review**. Company confirmation: **not yet given**.

| Field | State | Accepted value |
|---|---|---|
| revenue | ready | 120000 |
| cash_on_hand | ready | 420000 |
| arr | ready | 1200000 |
| management_context | ready | Revenue increased USD 20,000 versus July: USD 10,000 more recurring subscription revenue and USD 10,000 mor... |
| risks | ready | A customer contributing USD 30,000 MRR renews in November 2026; renewal is unsigned. Proposal planned by Oc... |
| help_requested | ready | Introductions to two hospital operations leaders and a referral for a fractional finance lead. |

Next questions:

None. Show the company its review preview.

## Missing

State: **needs_information**. Company confirmation: **not yet given**.

| Field | State | Accepted value |
|---|---|---|
| revenue | ready | 120000 |
| cash_on_hand | missing | Not populated |
| arr | missing | Not populated |
| management_context | missing | Not populated |
| risks | missing | Not populated |
| help_requested | missing | Not populated |

Next questions:

1. What was your cash balance in USD as of 2026-08-31?
2. What was your ARR in USD as of 2026-08-31, and how do you define it? If not applicable, please say so.
3. What changed during this reporting period, and what explains those changes?

2 additional questions deferred until a later turn.

## Conflict

State: **needs_information**. Company confirmation: **not yet given**.

| Field | State | Accepted value |
|---|---|---|
| revenue | conflicting | Not populated |
| cash_on_hand | conflicting | Not populated |
| arr | ready | 1200000 |
| management_context | ready | Revenue increased USD 20,000 versus July: USD 10,000 more recurring subscription revenue and USD 10,000 mor... |
| risks | ready | A customer contributing USD 30,000 MRR renews in November 2026; renewal is unsigned. Proposal planned by Oc... |
| help_requested | ready | Introductions to two hospital operations leaders and a referral for a fractional finance lead. |

Next questions:

1. We found conflicting values for revenue. Which is correct? Please confirm currency, units and reporting date where relevant.
2. We found conflicting values for cash on hand. Which is correct? Please confirm currency, units and reporting date where relevant.

## Wrong Period

State: **needs_information**. Company confirmation: **not yet given**.

| Field | State | Accepted value |
|---|---|---|
| revenue | needs_clarification | Not populated |
| cash_on_hand | needs_clarification | Not populated |
| arr | missing | Not populated |
| management_context | missing | Not populated |
| risks | missing | Not populated |
| help_requested | missing | Not populated |

Next questions:

1. Please clarify revenue: reporting period missing or wrong.
2. Please clarify cash on hand: as of date missing or wrong.
3. What was your ARR in USD as of 2026-08-31, and how do you define it? If not applicable, please say so.

3 additional questions deferred until a later turn.

## Resolved

State: **ready_for_review**. Company confirmation: **not yet given**.

| Field | State | Accepted value |
|---|---|---|
| revenue | ready | 120000 |
| cash_on_hand | ready | 420000 |
| arr | ready | 1200000 |
| management_context | ready | Revenue increased USD 20,000 versus July: USD 10,000 more recurring subscription revenue and USD 10,000 mor... |
| risks | ready | A customer contributing USD 30,000 MRR renews in November 2026; renewal is unsigned. Proposal planned by Oc... |
| help_requested | ready | Introductions to two hospital operations leaders and a referral for a fractional finance lead. |

Next questions:

None. Show the company its review preview.
