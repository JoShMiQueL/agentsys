# Architectural decisions

## One model, many logical agents (2026-10-21)

16GB VRAM makes multi-model setups mostly offload-bound. Roles implemented as
separate sessions/contexts on shared weights, not separate models.
Exception: `deep` (27B) as quality escalation, and optional Devin cloud agents.

## Artifact-first communication

16K ctx is the real bottleneck for RE pipelines (pseudocode, dumps, tool schemas).
Subagents write long output to disk and return <=200-word summaries + paths —
the filesystem is the shared memory. Mirrors REA's Evidence pattern.

## REA via bash CLI, not MCP

REA advertises ~200 tool schemas (~249K tokens) — instantly overflows local
context. `REA_MCP_TOOL_FAMILIES` scoping is still an open PR. Meanwhile,
`npx rea-agents <cmd>` via bash gives full access with zero schema cost and
on-demand discovery (`--help`, `--token-limit`, `--format json`).

## JSON config agents vs .md files

`agents` in opencode.json chosen for single-file install/merge. Per-project
agent customization may use `.opencode/agent/*.md` later — equivalent semantics.

## Two profiles

`reversing` = local abliterated models (privacy, no refusals, offline).
`devin` = optional cloud agents for general work when quality/speed matters and
privacy is not a concern (plugin `opencode-devin`, swe-2-* models).
Merged into one config; names prefixed `d*` to avoid collisions.

## SDD enforcement, memory re-injection, global install (2026-10-22)

- **Soft SDD enforcement** chosen over an `sdd-guard` plugin: skills + commands +
  prompt rules in primary agents. Escalate to a plugin only if agents skip specs
  in practice.
- **`instructions[]` config** chosen for post-compaction memory re-injection over
  a `context-keeper` plugin — zero-code path; OpenCode re-reads instruction files
  as the post-compaction baseline (see `.opencode/proposals/context-hooks.md`).
  The plugin remains the fallback if instruction reload proves insufficient.
- **Global SDD/memory install**: install.ps1 copies `.opencode/skills/` →
  `~/.config/opencode/skills/`, `.opencode/commands/` → `~/.config/opencode/
  commands/`, and `.opencode/memory/*.md` → `~/.config/opencode/memory/` so any
  project gets the workflow. Specs and proposals stay project-local on purpose.

## `.agents/` → `.opencode/` migration (2026-10-22)

Migrated the whole `.agents/` tree into `.opencode/` — the native OpenCode 2
project dir — for a single-harness, all-native layout (user decision; OpenCode 2
only for now). `.opencode/agent/` is a reserved native path, so project memory
lives in `.opencode/memory/` instead. Moved: `skills/`, `specs/`, `proposals/`
as-is; the four root .md files → `memory/`; `~/.config/opencode/agents-memory/`
renamed to `~/.config/opencode/memory/` in install.ps1 + `instructions[]`.

## Per-project memory via `-InitProject` templates (2026-10-22)

Reversed the global-memory part of the "global install" decision above:
install.ps1 no longer syncs `.opencode/memory/*` → `~/.config/opencode/memory/`.
Rationale: project memory must not leak across projects — agentsys's
decisions.md/gotchas.md would pollute every other repo's context. Now:

- **Global** (installed once): agents, plugins, skills, commands — methodology,
  not project content.
- **Per-project** (seeded on demand): `templates/opencode/` → `<project>/
  .opencode/` via `install.ps1 -InitProject [path] [-Force]` (like spec-kit's
  `specify init`). Seeds are generic versions of the four memory files plus
  specs/proposals dirs; existing files are never clobbered without `-Force`.
- `instructions[]` in both system.json changed to `.opencode/memory/*.md`
  (project-relative), so memory reloads post-compaction from the repo itself.
