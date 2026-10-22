---
name: sdd-converge
description: Load when all tasks in tasks.md are resolved — re-verifies every acceptance criterion in requirements.md and closes (or reopens) the spec.
---

# sdd-converge — final verification

Goal: prove every AC in `.opencode/specs/<slug>/requirements.md` holds against
the produced artifacts, then close the spec.

## Preconditions
- `tasks.md` has no unchecked `- [ ]` items (or `[!]` items are explained).

## Method

1. Read `requirements.md`. Extract every `AC-n:` line into a checklist.
2. For EACH AC, delegate verification to a `*-qa` subagent:
   - give it the AC text + paths to relevant artifacts (from design.md's
     requirement→change map);
   - qa must produce a concrete verdict: PASS (with evidence path/command
     output) or FAIL (with what's missing).
3. Record results — append to `state.md` log:

```
- converge: AC-1 PASS (evidence: <path|command>)
- converge: AC-2 FAIL (<reason>)
```

4. Verdict:
   - **All PASS** → set `stage: converged`, `status: closed`, append
     `- converge: all N criteria verified`. Spec is done.
   - **Any FAIL** → set `stage: implement` (reopen), add new `- [ ]` task(s)
     to `tasks.md` addressing the failures, increment `loop:`. Return to
     `sdd-implement`.
   - **AC now invalid** (scope changed) → amend requirements.md with a
     `> amended:` note on the AC line; never silently delete criteria.
5. Optionally delegate a final `*-reviewer` pass over the complete diff —
   required if the spec touched >2 subsystems.
6. Return: verdict + per-AC status + spec path. Compact — details live in
   state.md.

## state.md transition
`implement` → `converged` (closed) only on all-PASS; back to `implement`
on any FAIL. `converged` is terminal — reopening requires a new spec or an
explicit user request.
