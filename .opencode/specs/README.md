# Specs — spec-driven development workspace

One directory per feature/bugfix, named by kebab-case slug. Created and
advanced via `/sdd-specify`, `/sdd-plan`, `/sdd-tasks`, `/sdd-implement`,
`/sdd-converge` (skills in `.opencode/skills/`).

## Layout per `<slug>/`

| File | Written by | Contents |
|---|---|---|
| `requirements.md` | sdd-specify | Context + acceptance criteria in EARS notation (`WHEN … THE SYSTEM SHALL …`) |
| `design.md` | sdd-plan | Approach, files touched, requirement→change map, risks, constitution check |
| `tasks.md` | sdd-tasks | Ordered `- [ ]` tasks, each with agent assignment, files, AC refs, verify step |
| `state.md` | all stages | `stage:` (specify\|plan\|tasks\|implement\|converged), `status:`, `loop:` counter, append-only `log:` |

## Rules

- All specs must satisfy `.opencode/memory/constitution.md`.
- Stage order is linear: specify → plan → tasks → implement → converged.
  A converge failure reopens `implement`.
- `state.md` is the single source of truth for where a spec stands — check
  it before loading any sdd-* skill.
