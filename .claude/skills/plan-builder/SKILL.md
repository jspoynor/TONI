---
name: plan-builder
description: Grill you about a new feature, then write plans/<name>.md with its specs and a task list.
disable-model-invocation: true
---

Turn a feature idea into a plan document at `plans/<name>.md`: specs pinned down through a
grill session, followed by the task list to build it.

## Steps

1. **Get the feature.** If the user already described the feature when invoking this skill,
   use that. Otherwise ask what feature the plan is for.

2. **Name the file.** Ask the user what to name it, suggesting a kebab-case default derived
   from the feature (e.g. a "bulk link import" feature → `bulk-link-import.md`). If
   `plans/<name>.md` already exists, say so and ask whether to overwrite or pick a different
   name — never overwrite silently.

3. **Grill the spec.** Invoke the `grilling` skill on the feature. Do not draft the plan
   file until the grill ends with the user explicitly confirming the spec is settled —
   every branch grilling raised needs a resolved answer, not just the ones asked first.

4. **Write the plan.** Match the heading style already used in `plans/` (e.g.
   `plans/unsubscribe-link.md`, `plans/analytics-tracking.md`):
   - Title + short intro paragraph giving the feature's purpose and any constraint driving
     its shape.
   - `## Specs` — the grilled decisions, grouped by area, each as a stated decision plus its
     reason (not a transcript of the questions).
   - `## Data model` — only if the feature touches Firestore or another persisted shape.
   - `## Implementation tasks` — phased, numbered, concrete enough to execute without
     re-deriving the decisions in Specs.
   - `## Out of scope (deliberately)` — anything the grill explicitly ruled out, so it isn't
     re-litigated later.
   Write the file to `plans/<name>.md`.

5. **Confirm.** Tell the user the file path and give a one-line summary of what's in it.

## Completion criterion

`plans/<name>.md` exists, its Specs section reflects what the user actually agreed to in the
grill (not an assumption filled in after it stalled), and every task in Implementation tasks
traces back to a decision made in Specs.
