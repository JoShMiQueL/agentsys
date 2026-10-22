---
name: sdd-implement
description: Load when tasks.md has unchecked items — delegates each task, ticks checkboxes, runs the coder→qa→reviewer quality gate.
---

# sdd-implement — execute tasks

Goal: implement every unchecked `- [ ]` task in `.opencode/specs/<slug>/tasks.md`.

## Preconditions
- `state.md` shows `stage: tasks` (or `implement` resuming). On first run,
  set `stage: implement` and log `- implement: started`.

## Method — per task, in order

1. Read the task. Confirm its `files:` match design.md — drift means the
   design is stale; update design.md first or escalate.
2. Delegate to the agent named in the task (e.g. `gen-coder`). Hand it:
   - the task text + `verify:` line,
   - PATHS to design.md/requirements.md (not their contents),
   - artifact-first rule: subagent writes code, returns <=200-word summary.
3. On subagent completion, verify its claim yourself: run the `verify:`
   check, or inspect the artifact. Do not tick a box on faith.
4. Tick the checkbox in `tasks.md` (`- [x]`), append to `state.md` log:
   `- implement: T<N> done (qa pass | qa fail loop=<n>)`.
5. **Quality gate** per task:
   - delegate verification to `*-qa` subagent against the task's `verify:` +
     relevant ACs;
   - qa REJECT → delegate fix to coder, increment `loop:` in `state.md`;
   - `loop` > 3 total for the spec → escalate to `*-deep` or report blocker
     to the user. Do not silently retry forever.
6. If a task proves impossible as written, mark it `- [!]` with a reason
   inline, log it, and stop — report to orchestrator.

## Rules
- ONLY unchecked tasks may be implemented — never add scope mid-run.
- New files go where design.md says; deviations require updating design.md
  and logging in state.md.
- Keep replies compact: task list status + paths changed.

## state.md transition
`tasks` → `implement` on first run. When all boxes are `[x]` or `[!]`,
append `- implement: all tasks resolved`; `sdd-converge` advances the stage.
