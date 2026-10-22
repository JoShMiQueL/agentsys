# agentsys — installable multi-system agent collections for OpenCode 2

Multiple systems coexist safely: each is a named set of agents merged into
`~/.config/opencode/opencode.json`. No collisions — agents are namespaced
(`re`/`re-explorer`/`re-coder`/`re-analyst`/`re-deep` vs `gen`/`gen-explore`/`gen-coder`/`gen-analyst`)
and each primary knows its own roster by exact name.

**Default system = `general`** — provider-agnostic roster (`gen`/`gen-*`);
agents define no `model`, so they inherit the global `model` from
`opencode.json` (whatever provider the user configured). It sets
`default_agent: gen` only. **`reversing` is an optional local profile**
(abliterated Ollama agents `re`/`re-*`) for RE/privacy/offline work — its
`models.json` is a recommended preset, not a requirement (edit `model` fields
for your own Ollama models). It declares no top-level defaults, so installing
it never steals the default; switch explicitly via `/agent re` or
`opencode2 run --agent re`. A provider-specific roster (e.g. Devin's
`swe-2-*` via `opencode-devin`) is a documented customization, not a shipped
system.

Read `.opencode/memory/` for persistent memory before changing anything.

## Layout

- `systems/<name>/system.json` — config fragment (agents/providers/permissions/defaults)
- `systems/<name>/models.json` + `models/` — Ollama aliases required (optional)
- `install.ps1` — idempotent installer (`-Systems a,b`, `-SkipModels`,
  `-InitProject <path> [-Force]`)
- `templates/opencode/` — per-project `.opencode/` seed (memory/, specs/,
  proposals/) copied by `install.ps1 -InitProject`
- `merge_config.py` — deep-merge with auto-backup of opencode.json
- `tools/bench/` — Ollama multi-model benchmark suite
- `tools/opencode-debug/` — session DB inspection + config schema probes
- `.opencode/` — the OpenCode-2-native project dir: `memory/` (models.md, gotchas.md,
  decisions.md, constitution.md), `specs/<slug>/`, `skills/`, `proposals/`, `commands/`.
  Memory lives in `memory/` because `.opencode/agent/` is a reserved native path.

## SDD (spec-driven development)

Orchestrators follow a spec-first workflow: requests that create/modify >2 files,
span >1 subsystem, or are features/refactors produce a spec under
`.opencode/specs/<slug>/` (`requirements.md`, `design.md`, `tasks.md`, `state.md`)
before implementation. Workflow skills live in `.opencode/skills/sdd-*` and all
specs must honor `.opencode/memory/constitution.md`. Design rationale:
`.opencode/proposals/sdd-design.md`.

## Install / sync

```powershell
git pull
.\install.ps1                            # general system (default)
.\install.ps1 -Systems general,reversing # several systems side by side
.\install.ps1 -Systems reversing       # local RE profile only
.\install.ps1 -SkipModels
.\install.ps1 -InitProject .           # seed .opencode/ into the current project
```

Global install covers agents/plugins/skills/commands only — project memory is
per-repo: `-InitProject` copies `templates/opencode/` → `<path>/.opencode/`
(skips existing files unless `-Force`).

Top-level defaults (`model`, `default_agent`) are last-write-wins across
systems. Agents without a `model` field inherit the global `model`; those with
one keep their own. Switch systems by choosing the agent (`/agent re` or
`opencode2 run --agent re`).

## Hard-won rules (details in .opencode/memory/gotchas.md)

- v2 schema: `agents`+`system`+`model` (deprecated `agent`/`prompt` are ignored)
- gpt-oss-abliterated requires `think:"low"`; `think:false` does not disable thinking
- Headless hangs come from out-of-workspace permission prompts — fixed via `permissions`
- Agent names stay English; models hallucinate translated names
- REA is driven via bash `npx rea-agents <cmd>`, NOT MCP (~249K-token catalog)
