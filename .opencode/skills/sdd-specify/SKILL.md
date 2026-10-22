---
name: sdd-specify
description: Load when starting a new spec — writes EARS-style requirements.md and initializes state.md for .opencode/specs/<slug>/.
---

# sdd-specify — write requirements

Goal: produce `.opencode/specs/<slug>/requirements.md` + `state.md`. Nothing else.

## Inputs
- `$ARGUMENTS` = slug (kebab-case feature/bugfix name) + user intent.
- Read `.opencode/memory/constitution.md` first — requirements must not violate it.

## Method

1. Create `.opencode/specs/<slug>/`.
2. Write `requirements.md`:

```markdown
# <slug> — requirements

## Context
<2-4 lines: what exists today, why this is needed>

## Acceptance criteria (EARS)
- AC-1: WHEN <trigger/condition> THE SYSTEM SHALL <observable behavior>
- AC-2: WHILE <state> THE SYSTEM SHALL <behavior>
- AC-3: IF <invalid input> THEN THE SYSTEM SHALL <error behavior>
- AC-4: THE SYSTEM SHALL <unconditional invariant>

## Out of scope
- <explicit non-goals>
```

EARS rules:
- One behavior per criterion; every criterion must be **verifiable** by a
  qa subagent inspecting artifacts or running commands — no "should be fast".
- Use `WHEN` for events, `WHILE` for state-dependent, `IF/THEN` for errors,
  bare `SHALL` for invariants.
- 3-10 criteria typical. More ⇒ split the spec.

3. Write `state.md`:

```markdown
# state — <slug>
stage: specify
status: active
loop: 0
created: <YYYY-MM-DD>
log:
- specify: requirements.md written
```

4. Return: slug path + criterion count. Do NOT write design.md or tasks.md —
   that is `sdd-plan` / `sdd-tasks`.

## state.md transition
Write `stage: specify` at creation. Do not advance the stage; `sdd-plan`
sets `stage: plan` when it starts.
