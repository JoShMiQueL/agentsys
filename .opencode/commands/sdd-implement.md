---
description: Execute all unchecked tasks in tasks.md, ticking boxes and running the coder→qa→reviewer quality gate per task
agent: gen
subtask: true
---

Load the `sdd-implement` skill and follow it exactly.

Slug: `$1`. Spec dir: `.opencode/specs/$1/`

Steps:
1. Read `.opencode/specs/$1/state.md` and `.opencode/specs/$1/tasks.md`.
   If no unchecked tasks exist, report that and stop.
2. Set `stage: implement` in state.md on first run; log `implement: started`.
3. For each `- [ ]` task in order: delegate to its assigned agent with
   artifact-first instructions, verify its `verify:` claim yourself, then
   tick `- [x]`, log to state.md, and run the `gen-qa` quality gate.
4. REJECT → fix via coder, `loop:` +1. `loop > 3` → escalate or report blocker.
5. Impossible task → mark `- [!]` with reason, stop, report.

Implement ONLY listed tasks — no scope additions mid-run.

Return: per-task status + changed paths + final loop count.
