# Project constitution

Principles every spec (and its implementation) MUST satisfy. A design that
violates a principle is rejected at the plan stage; a task that violates one
is rejected by qa/reviewer.

## Communication
- **Artifact-first.** Long output goes to disk; agents return <=200-word
  summaries + paths. The filesystem is shared memory — never paste dumps.
- **Paths, not content.** Orchestrator hands subagents file paths, not blobs.

## Naming & language
- Agent names and prompts stay **English** — local models hallucinate
  translated names and invented tool args.
- Specs, skills, commands, and commit messages in English.

## Config (opencode v2)
- Schema keys: `agents` + `system` + `model`. `agent`/`prompt`/`small_model`
  are silently ignored — never use them.
- No `deny` rules in `permissions` where agents need feedback: a configured
  deny short-circuits before `permission.hook("evaluate")`. Use a plugin
  that sets `effect="deny"` + `message` instead.
- `merge_config.py` only APPENDS list-of-dicts — removals need manual cleanup
  of installed `opencode.json`.

## Process
- **Spec-first gate:** >2 files changed, >1 subsystem, or "feature/refactor/
  implement" ⇒ spec required before delegation. Trivial fixes may skip with
  a one-line note in `state.md`.
- **Quality gate:** every implemented task runs coder → qa → reviewer.
  REJECT increments `state.md` loop counter; >3 escalates to deep agent or
  reports a blocker.
- **Convergence:** a spec closes only when every EARS criterion in
  `requirements.md` is verified against artifacts — not just code compiling.

## Context discipline (16K local models)
- Skills load on demand; methodology never lives in the system prompt.
- Fixed file names (`requirements.md`, `design.md`, `tasks.md`, `state.md`)
  give deterministic anchors — agents fill slots, don't invent layouts.
- SKILL.md files stay ~40-80 lines; spec files stay terse and diffable.
