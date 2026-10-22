# Project constitution

Principles every spec (and its implementation) MUST satisfy. A design that
violates a principle is rejected at the plan stage; a task that violates one
is rejected by qa/reviewer. Adapt these to the project.

## Communication
- **Artifact-first.** Long output goes to disk; agents return <=200-word
  summaries + paths. The filesystem is shared memory — never paste dumps.
- **Paths, not content.** Orchestrator hands subagents file paths, not blobs.

## Naming & language
- Agent names and prompts stay **English** — models hallucinate translated
  names and invented tool args.
- Specs, skills, commands, and commit messages in English.

## Process
- **Spec-first gate:** >2 files changed, >1 subsystem, or "feature/refactor/
  implement" ⇒ spec required before delegation. Trivial fixes may skip with
  a one-line note in `state.md`.
- **Quality gate:** every implemented task runs coder → qa → reviewer.
- **Convergence:** a spec closes only when every acceptance criterion in
  `requirements.md` is verified against artifacts — not just code compiling.

## Context discipline
- Skills load on demand; methodology never lives in the system prompt.
- Fixed file names (`requirements.md`, `design.md`, `tasks.md`, `state.md`)
  give deterministic anchors — agents fill slots, don't invent layouts.
