---
description: Decompose design.md into tasks.md — ordered checkboxed tasks, each sized for one subagent delegation
agent: gen
subtask: true
---

Load the `sdd-tasks` skill and follow it exactly.

Slug: `$1`. Spec dir: `.opencode/specs/$1/`

Steps:
1. Read `.opencode/specs/$1/requirements.md` and `.opencode/specs/$1/design.md`.
   If design.md is missing, stop and tell the orchestrator to run
   `/sdd-plan $1` first.
2. Write `.opencode/specs/$1/tasks.md`: ordered `- [ ]` tasks, each with
   `(agent)` assignment, `files:`, `satisfies: AC-n`, and `verify:`.
   One task = one delegation; split anything touching >3 files.
3. Confirm every AC is covered by ≥1 task's `satisfies:` field.
4. Update `.opencode/specs/$1/state.md`: `stage: tasks`, log entry.

Return: tasks path + task count + AC coverage report.
