---
name: execute
description: Orchestrate subagents to carry out a plan file's tasks end-to-end — one at a time, verified and committed before moving to the next.
disable-model-invocation: true
---

Own a plan file: drive it from first task to last through subagents you dispatch, verify, and
commit — without writing the feature's code yourself.

## Steps

1. **Get the plan.** If a file path was given at invocation, use it. Otherwise ask which
   `plans/*.md` file to execute. Read it in full — the task list plus whatever Specs section
   justifies each task, since a subagent working from the task line alone will guess at
   decisions the plan already made.

2. **Build the task order.** Take the tasks from the plan's task list section in the order
   they're written. That order is chronological — do not reorder, parallelize, or skip ahead
   even if a later task looks independent.

3. **Dispatch one subagent per task.** For the current task, spawn exactly one subagent
   (general-purpose, foreground — not `run_in_background`, and without worktree isolation;
   this project works directly in the main checkout) with: the task's own text, the plan
   sections it depends on, and the file paths it touches. Never advance to the next task while
   this one still has a subagent outstanding, and never run two subagents at once.

4. **Gate the work.** When the subagent reports back, verify its work yourself before
   accepting it — read the diff, run the project's build/test/lint commands, and check the
   result against what the plan actually specified for that task. A subagent's self-report of
   success is not verification. Do not accept work you aren't happy with.
   - If it passes the gate, move to step 5.
   - If it doesn't, send the same subagent (or a fresh one, your judgment) back with the
     specific gap — do not lower the bar to move on, and do not fix it yourself in place of
     the subagent. Re-gate every retry the same way.

5. **Commit.** Once a task clears the gate, commit it — locally, on the current branch, one
   commit per task. Never branch, push, or deploy, even when the plan's own tasks tell you to;
   leave those steps for the user to run by hand.

6. **Repeat.** Continue through the remaining tasks in order. When the last one clears the
   gate and is committed, report back to the user once: what was built, and the commits that
   carry it.

## Completion criterion

Every task in the plan's task list has a subagent-produced, gate-verified, locally-committed
change — none skipped, none accepted below standard — and the branch is exactly where it
started: no branch created, nothing pushed, nothing deployed.
