---
description: Final gate — re-verify every acceptance criterion in requirements.md against artifacts; close spec only when all PASS
agent: gen
subtask: true
---

Load the `sdd-converge` skill and follow it exactly.

Slug: `$1`. Spec dir: `.opencode/specs/$1/`

Steps:
1. Read `.opencode/specs/$1/requirements.md`, `tasks.md`, `state.md`.
   If tasks.md has unchecked items, stop — run `/sdd-implement $1` first.
2. For EACH `AC-n` criterion, delegate verification to `gen-qa`; it must
   return PASS (with evidence) or FAIL (with gap). No self-verification.
3. Log every verdict to state.md.
4. All PASS → `stage: converged`, `status: closed`. Any FAIL → back to
   `stage: implement`, append new `- [ ]` fix tasks to tasks.md, `loop:` +1,
   and tell the orchestrator to re-run `/sdd-implement $1`.
5. If the spec touched >2 subsystems, also get a `gen-reviewer` pass on the
   full diff before closing.

Return: per-AC verdict table + final spec status.
