---
description: Write design.md for an existing spec (architecture, files touched, risks, constitution check)
agent: gen
subtask: true
---

Load the `sdd-plan` skill and follow it exactly.

Slug: `$1`. Spec dir: `.opencode/specs/$1/`

Steps:
1. Read `.opencode/specs/$1/requirements.md` — every AC must be mapped.
   If missing, stop and tell the orchestrator to run `/sdd-specify $1` first.
2. Read @.opencode/memory/constitution.md and @.opencode/memory/gotchas.md.
3. Explore the codebase (delegate broad searches to `gen-explore`) to name
   real files; return paths, not dumps.
4. Write `.opencode/specs/$1/design.md` per the skill's template, including the
   requirement→change map and constitution check.
5. Update `.opencode/specs/$1/state.md`: `stage: plan`, log entry.

Return: design path + files-touched count + any unmappable ACs.
