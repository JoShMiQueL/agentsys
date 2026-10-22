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

## Generalized systems for public use (2026-10-22)

Decoupled rosters from specific providers/models so the repo works for anyone:

- **`general`** is the new default system — provider-agnostic `gen`/`gen-*`
  roster. Agents omit `model` entirely (verified optional in
  `Config.AgentEncoded`, opencode.ai/config.json — no `required` list), so they
  inherit the user's global `model` from opencode.json. It declares
  `default_agent: gen` but no top-level `model` and no `plugins`.
- **`devin` removed as a shipped system** — it was a personal provider config.
  Now a documented customization: add the plugin to `plugins` + set `model`
  fields. User's own devin config stays in their opencode.json.
- **`reversing` stays optional** with the same roster; its `models.json`
  (glmflash-abl/gptoss-abl/qwen38-abl aliases) is a *recommended preset*, not a
  requirement — users with their own Ollama models edit `model` fields or skip
  model creation (`-SkipModels`). Installers already tolerate absent
  models.json.
- **install.sh default fixed** (`reversing` → `general`) — was a divergence bug
  vs install.ps1, which now defaults to `general` too.

## User overrides overlay + shared-key unmerge fix (2026-10-22)

- **Overlay mechanism chosen** for durable per-user/per-agent overrides:
  `~/.config/opencode/agentsys-overrides.json`, merged last by cli.py and
  install.ps1. Survives `git pull`, `agentsys sync`, and `update` (which wipes
  INSTALL_DIR). Hand-editing opencode.json only worked for systems that don't
  define the key (general's `model`); the overlay works for all three cases.
- **Location = config dir, not `~/.agentsys/`** — `cmd_uninstall` rmtree's
  INSTALL_DIR and the irm-bootstrap wipes `$Dest\*` on reinstall; the config
  dir survives both. Uninstall unmerges the overlay but keeps the file.
- **`remove()` re-merges survivors**: unmerge-only stripped keys shared by
  multiple systems (`instructions` contributed by general+reversing vanished
  when removing one). New order: pop state → unmerge removed frag → re-merge
  every remaining installed system → overlay.
- **List append-only limitation accepted**: overlay can add permission/
  instruction items but cannot subtract; subtraction syntax is out of scope.
- Overlay-overridden agents leave stubs on remove — documented as by-design.
- `merge_config.py` stays overlay-agnostic; only install.ps1 appends the
  overlay path to `@frags`. Full rationale: `.opencode/proposals/
  user-overrides-design.md`.

## Snapshot-based remove supersedes re-merge-only fix (2026-10-22)

- `install()` now snapshots the merged fragment into
  `agent-systems.json` (`installed.<name>.fragment`). `remove()` unmerges the
  SNAPSHOT, not live `system.json` — uninstalls stay correct even if the repo
  fragment changed after install (git pull renamed an agent, etc.).
- Plain `unmerge` only deletes keys equal to the fragment value, leaving
  diverged stubs (residue). `remove()` therefore hard-deletes each
  fragment-defined agent unless a surviving system's fragment or the overlay
  defines it, and force-pops `default_agent`/`model` the fragment owned
  (restored by survivors/overlay when they define them).
- `cmd_uninstall` uses the same path + drops cfg agents owned by no system
  and no overlay. `cmd_doctor` reports `[warn] agent X untracked` for cfg
  agents owned by neither — residue now surfaces instead of hiding.
- Legacy state entries (no `fragment` key) fall back to live system.json.
