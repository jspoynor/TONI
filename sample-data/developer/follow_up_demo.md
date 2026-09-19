# Scripted follow-up conversation

All answers are authored synthetic fixtures, not facts recovered from the incomplete upload. Use only `02_income_only_missing_context.pdf` for this scenario. Do not give the model this answer script or the complete PDF in its initial extraction prompt.

**Nemo, turn 1 (three questions):**
1. What was your cash balance in USD as of August 31, 2026?
2. What was your ARR in USD at August 31, and what does it include?
3. Revenue increased from USD 100,000 in July to USD 120,000 in August. What explains the change?

**Company:** Cash was 420,000. ARR was USD 1.2 million at August 31, based on USD 100,000 in live recurring MRR times 12. It excludes implementation fees and contracts that are not yet live. A hospital deployment added USD 10,000 in recurring subscription revenue and USD 10,000 more one-time implementation revenue compared with July.

**Nemo, turn 2:**
1. Please confirm that the 420,000 cash balance is USD and is dated August 31, 2026.
2. What material risks should the VC know about, and what are you doing about them?
3. What specific help would you like from the VC?

**Company:** Yes, cash is USD 420,000 as of August 31. One customer with USD 30,000 MRR renews in November, and the renewal is unsigned. Our account lead will present a proposal by October 1. Please introduce us to two hospital operations leaders and recommend a fractional finance lead.

**Expected next action:** Present a review draft. Preserve revenue's PDF page-1 source; use conversation turn IDs for cash, ARR, context, risks, and asks. Management claims stay attributed to management. Do not say the customer has churned. Do not manufacture a clinical benefit.

**Company confirmation:** “I confirm the six fields in this preview for August 2026.”

**Expected submission:** Freeze a version of the reviewed values and mark those six fields confirmed. Record the confirmation time and who confirmed it in the actual application. A later answer changes a draft, not that submitted snapshot.

## Separate correction test

**Company:** “Correction: cash at August 31 was USD 415,000, not USD 420,000.”

**Expected:** New draft candidate 415,000 with source = this message; require review before resubmission. Preserve the old submitted snapshot. Ask for a revised balance sheet/cash-flow statement or explanation because the uploaded statements still show 420,000; do not silently change their other line items to force reconciliation.
