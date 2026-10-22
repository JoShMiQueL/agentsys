---
name: sdd-plan
description: Load when a spec has requirements.md — produces design.md (architecture, files touched, risks, constitution check).
---

# sdd-plan — write design

Goal: produce `.opencode/specs/<slug>/design.md` from `requirements.md`.

## Preconditions
- `.opencode/specs/<slug>/requirements.md` exists. If not, run `sdd-specify` first.
- Read `.opencode/memory/constitution.md`, `.opencode/memory/gotchas.md`, relevant memory.

## Method

1. Explore the codebase enough to name real files. Delegate broad exploration
   to `*-explore`/`*-explorer` — return paths + 1-line facts, not dumps.
2. Write `design.md`:

```markdown
# <slug> — design

## Approach
<2-6 lines: the chosen strategy and why>

## Architecture / changes
- `path/to/file1` — <what changes and why>
- `path/to/file2` — <...>
- NEW `path/to/newfile` — <purpose>

## Requirement → change map
- AC-1 → file1 (how it is satisfied)
- AC-2 → file2, newfile

## Risks / gotchas
- <concrete risk + mitigation; cite .opencode/memory/gotchas.md where relevant>

## Constitution check
- [ ] artifact-first respected (no dumps planned)
- [ ] v2 schema keys only (if config touched)
- [ ] English names/prompts
- [ ] fits 16K ctx (on-demand loading, fixed paths)
```

3. Every AC from requirements.md MUST appear in the map. If one can't be
   mapped, the design is incomplete — fix it or flag a blocked AC.
4. Update `state.md`: set `stage: plan`, append `- plan: design.md written`
   to `log`.
5. Return: design path + files-touched count + any blocked ACs.

## state.md transition
`specify` → `plan` on start. Do not advance to `tasks`; that is `sdd-tasks`.
