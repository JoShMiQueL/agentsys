# SDD (Spec-Driven Development) design for agentsys

Status: **proposal** — no code changes yet.
Author: deep subagent, 2026-10-22.

## Goal

Extend `.opencode/` beyond passive memory (models/gotchas/decisions) into an
active SDD workspace: specs the orchestrator produces before delegating,
quality gates wired to existing `*-qa` / `*-reviewer` subagents, and
opencode-2-native primitives (commands, skills, rules) so SDD is *enforced*,
not aspirational.

## 1. OpenCode 2 primitives that exist TODAY (verified against docs)

Source: https://opencode.ai/docs/{commands,skills,rules,agents,plugins}

| Primitive | Path / config | What it gives SDD |
|---|---|---|
| **Custom commands** | `.opencode/commands/<name>.md` (project) or `~/.config/opencode/commands/` (global); also `command` key in `opencode.json`. Supports `$ARGUMENTS`, `$1..$N`, `` !`shell` `` injection, `@file` refs, frontmatter `description`/`agent`/`subtask`/`model`. | Slash-invoked SDD stages: `/specify`, `/plan`, `/tasks`, `/implement`, `/converge`, `/bug-assess`, etc. Commands can pin `agent: re` or `agent: gen` and force `subtask: true` so the stage runs in a subagent and doesn't pollute orchestrator context. |
| **Agent skills** | `.opencode/skills/<name>/SKILL.md` (project — lands inside our `.opencode/` project dir), `.agents/skills/`, `.claude/skills/`, plus global variants. YAML frontmatter `name`, `description`; metadata `opencode/slash: "true"` exposes as `/name`, `opencode/autoinvoke: "false"` hides from auto-selection. Loaded on-demand via native `skill` tool. | Reusable spec *methodology* (how to write requirements, how to decompose tasks) that agents load only when needed — keeps 16K ctx clean. Skill-per-SDD-stage fits perfectly. |
| **Rules / instructions** | `AGENTS.md` (project), `~/.config/opencode/AGENTS.md` (global), plus `instructions: [...]` array in `opencode.json` accepting globs and remote URLs. | The *always-on* SDD policy — e.g. "non-trivial work requires a spec" — lives in `AGENTS.md` or an `instructions`-listed file so it's in every session's context without a skill-load step. |
| **Agents** | `agents.<name>` in `opencode.json` (what we already use) or `.opencode/agent/<name>.md`. | Existing `re-*`/`gen-*` roster unchanged; SDD adds conventions for *what orchestrator hands them*. |
| **Permissions** | `permissions` ruleset + `permission.skill` patterns (`"internal-*": "deny"`, `"experimental-*": "ask"`). | Gate which agents can load which SDD skills; `ask` on mutating stages if desired. |
| **Plugins** | `~/.config/opencode/plugins/<name>/` auto-discovered; `permission.hook("evaluate")` can inject deny + message (see gotchas). | Optional: a plugin that denies `edit`/`write` when no `spec.md` exists for the current feature — the only way to *hard*-enforce spec-first. |

## 2. SDD landscape cross-check (late 2026)

- **GitHub spec-kit 1.0** (github.com/github/spec-kit, 142k★, Oct-2026):
  flow = `/speckit-constitution` → `/speckit-specify` → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-implement` → `/speckit-converge`.
  Artifacts under `.specify/`; extensions add bug-fix (`/speckit-bug-*`)
  and idea-assessment (`/speckit-assess-*`) flows. Key idea: *constitution*
  = project-level principles that constrain every later stage.
- **Kiro-style specs**: `.kiro/specs/<feature>/{requirements.md, design.md,
  tasks.md}` — requirements in EARS notation ("WHEN … THE SYSTEM SHALL …"),
  design doc, checkbox task list. Simpler than spec-kit, easy to mirror.
- **BMAD**: heavier role-play method (analyst → PM → architect → dev → QA),
  useful mainly for the *role-based delegation* pattern we already have.

We adopt the **kiro file shape** (3 files per feature — minimal, diffable)
with the **spec-kit stage names** (specify/plan/tasks/implement/converge)
since our agents already map to them, plus a **constitution** file.

## 3. Proposed `.opencode/` layout

```
.opencode/
  memory/              # project memory (.opencode/agent/ is reserved, so not `agents/`)
    models.md          # existing
    gotchas.md         # existing
    decisions.md       # existing
    constitution.md    # NEW — project principles every spec must satisfy
  specs/               # NEW — one dir per feature/bugfix
    <slug>/
      requirements.md  # EARS-style acceptance criteria
      design.md        # architecture, files touched, risks
      tasks.md         # ordered, checkboxed, agent-assignable tasks
      state.md         # NEW — stage machine: specify|plan|tasks|implement|converge, status, loop count
  skills/              # NEW — auto-discovered by opencode's skill tool
    sdd-specify/SKILL.md
    sdd-plan/SKILL.md
    sdd-tasks/SKILL.md
    sdd-implement/SKILL.md
    sdd-converge/SKILL.md
  proposals/           # NEW — design docs like this one (pre-spec ideas)
```

`.opencode/skills/` is a *supported* opencode discovery path — skills land in
the project-native dir, no separate `.agents/` needed. Commands can also live in
`.opencode/commands/` if we want `/specify` etc. as TUI slash commands
(distinct from skills, which are agent-invoked).

## 4. Workflow rules for the orchestrator prompt

Insert into `re` / `gen` system prompts (and mirror in `AGENTS.md`):

1. **Spec-first gate.** If the request creates/modifies >2 files, touches
   >1 subsystem, or the user says "feature/refactor/implement", the
   orchestrator MUST load `skill: sdd-specify`, produce
   `.opencode/specs/<slug>/requirements.md` + `design.md` + `tasks.md`
   (delegating drafting to `*-analyst`/`*-coder`), and only then delegate
   implementation. Trivial fixes (typos, single-file bugs) may skip with a
   one-line justification logged to `state.md`.
2. **Stage-gated delegation.** `*-coder` may only implement tasks listed
   and unchecked in `tasks.md`. After each task, orchestrator updates the
   checkbox + `state.md`, then runs the existing quality gate (`*-qa` →
   `*-reviewer`). REJECT increments `state.md` loop counter; >3 escalates
   to `re-deep` or reports blocker.
3. **Convergence check.** Before synthesizing the final answer, load
   `skill: sdd-converge`: re-run the full acceptance list from
   `requirements.md` against the produced artifacts via `*-qa`; only
   "all criteria verified" closes the spec (`state.md` → `converged`).

Optional hardening (later): a `plugins/sdd-guard` that denies `edit`/`write`
outside `.opencode/` when `state.md` for the active slug is missing or not in
`implement` stage — enforcement via the `permission.hook("evaluate")`
feedback pattern from gotchas.md, not a silent `deny` rule.

## 5. Why this fits our constraints

- **16K ctx**: skills are loaded on demand — spec methodology isn't in the
  system prompt until needed. Spec files live on disk; orchestrator passes
  *paths* to subagents, honoring artifact-first communication (decisions.md).
- **Local models hallucinate structure**: fixed file names + a tiny
  `state.md` state machine give deterministic anchors; agents fill slots,
  don't invent layouts.
- **Idempotent install**: `.opencode/` is already our dir; adding subdirs is
  `install.ps1`-friendly (copy, no merge). Only the orchestrator
  `system` strings in `system.json` need a paragraph appended.
