---
description: Start a new spec — write EARS requirements.md + state.md under .opencode/specs/<slug>/
agent: gen
subtask: true
---

Load the `sdd-specify` skill and follow it exactly.

Slug: `$1` (kebab-case). Remaining arguments describe the feature/bugfix:
`$ARGUMENTS`

Steps:
1. Read @.opencode/memory/constitution.md and @.opencode/memory/gotchas.md for constraints.
2. Create `.opencode/specs/$1/requirements.md` in EARS notation per the skill.
3. Create `.opencode/specs/$1/state.md` with `stage: specify`, `status: active`.
4. Do NOT write design.md or tasks.md — those are `/sdd-plan` and `/sdd-tasks`.

Return: spec directory path + number of acceptance criteria.
If `$1` is missing, ask the orchestrator for a slug — do not invent one.
