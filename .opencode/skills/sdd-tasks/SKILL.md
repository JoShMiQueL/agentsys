---
name: sdd-tasks
description: Load when design.md exists — decomposes it into tasks.md, an ordered checkboxed list sized for one subagent delegation each.
---

# sdd-tasks — decompose into tasks

Goal: produce `.opencode/specs/<slug>/tasks.md` from `design.md`.

## Preconditions
- `requirements.md` and `design.md` exist in `.opencode/specs/<slug>/`.

## Method

1. Write `tasks.md`:

```markdown
# <slug> — tasks

Ordered. Implement top-down; do not reorder without updating design.md.

- [ ] T1 (<agent>) <imperative description>
      files: `path/to/file1`
      satisfies: AC-1, AC-2
      verify: <concrete check, e.g. command to run or artifact to inspect>
- [ ] T2 (gen-coder) ...
```

2. Sizing rules:
   - One task = one subagent delegation = one focused diff. If it touches
     >3 files or needs 2 agents, split it.
   - Order dependencies first (schema/config before consumers).
   - Final task is usually "run quality gate over full diff" (qa agent).
3. Agent assignment — pick from the active roster:
   - `gen-explore`/`gen-analyst` for research, `gen-coder` for implementation,
     `gen-qa` for verification; `re-*` equivalents for reversing work;
     `*-deep` only for hard reasoning escalations.
4. Every AC in requirements.md must be covered by ≥1 task's `satisfies:`.
   List uncovered ACs in your reply if any remain — do not invent tasks
   outside design.md's scope.
5. Update `state.md`: `stage: tasks`, append `- tasks: N tasks written` to `log`.
6. Return: tasks path + task count + AC coverage.

## state.md transition
`plan` → `tasks`. Implementation begins when `sdd-implement` sets
`stage: implement`.
