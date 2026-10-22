# agentsys — multi-system agent collections for OpenCode 2

Each folder in `systems/` is a complete, installable agent system — one command
merges it into `~/.config/opencode/opencode.json` with no collisions (agents are
namespaced: `re`/`re-*` vs `gen`/`gen-*`).

- **`general` (default)** — provider-agnostic roster: a `gen` orchestrator plus
  `gen-explore`/`gen-coder`/`gen-analyst` subagents. Agents carry no `model`
  field, so they inherit whatever global `model` you already have in
  `opencode.json`. Sets `default_agent: gen` only.
- **`reversing` (optional local profile)** — local abliterated Ollama models for
  reverse-engineering / privacy-sensitive / offline work. Its `models.json` is a
  *recommended preset*, not a requirement: if you already run your own Ollama
  models, edit the `model` fields in `system.json` (or skip model creation with
  `-SkipModels`). It does NOT steal the default: switch explicitly with
  `/agent re` or `opencode2 run --agent re`.

Adding a new system = creating `systems/<name>/system.json`
(+ `models.json` optional).

## Bring your own models

`general` deliberately defines no models. Agents without a `model` field fall
back to your top-level `model` in `opencode.json` — set that once (any provider:
Anthropic, OpenAI, Ollama, a plugin provider...) and the whole roster uses it.
To pin a specific model per agent, add `"model": "provider/model"` to that
agent's entry in `systems/general/system.json` (or edit the merged
`opencode.json` after install). To use a plugin-backed provider (e.g. Devin
`swe-2-*` via `opencode-devin`), add the plugin to `plugins` and set models
accordingly.

## User overrides

`~/.config/opencode/agentsys-overrides.json` is an optional sparse overlay —
same schema as `system.json` — merged **last** by `cli.py` and `install.ps1`,
so it always wins over every installed system:

```json
{
  "agents": {
    "gen-coder": { "model": "ollama/devstral-abl:latest" },
    "re-deep":   { "model": "ollama/qwen38-abl:latest", "options": {"num_ctx": 32768} }
  }
}
```

- Survives `agentsys sync`, `update`, and `git pull`.
- `agentsys remove <name>` is a **total** uninstall: every agent the system
  defined is deleted from `opencode.json` (snapshot-based, zero residue) —
  **except** agents your overlay covers, which persist by design. Delete the
  overlay entry yourself if you want it gone.
- `agentsys uninstall` unmerges the overlay but keeps the file on disk.
- Limitation: lists are append-only — the overlay can add `permissions` or
  `instructions` items but cannot remove one a fragment contributed.
- `doctor` treats overlay-covered keys as intentional, not drift, and warns
  about untracked agents (residue owned by no installed system).

## Install

```powershell
# bun-style, no clone needed — installs the default (general) system.
# download, inspect, then run — avoids Defender's irm|iex heuristic:
iwr https://raw.githubusercontent.com/JoShMiQueL/agentsys/master/install.ps1 -OutFile install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

```sh
# unix equivalent (Linux/macOS):
curl -fsSL https://raw.githubusercontent.com/JoShMiQueL/agentsys/master/install.sh -o install.sh
sh install.sh
```

> **Troubleshooting — AV false positive:** Windows Defender may flag
> `irm | iex` as `Trojan:Win32/Commando.A!ml` — a false positive on the
> download-and-execute pattern. The two-step form above avoids it and lets
> you inspect the script before running it.

```powershell
# or locally after clone — general is the default:
.\install.ps1                            # general only
.\install.ps1 -Systems general,reversing # both side by side
.\install.ps1 -Systems reversing         # local RE profile only
.\install.ps1 -SkipModels -NoDeps        # skip Ollama models / dep auto-install

# seed .opencode/ (memory, specs, proposals) into a project:
.\install.ps1 -InitProject <path-to-project> [-Force]
```

Fully automatic: missing deps (Python 3.11, Ollama, Node/opencode2) are
installed via `winget`/`npm`. Use `-NoDeps` to fail instead of auto-installing.
`install.ps1` creates Ollama aliases declared in `models.json` (reversing only)
and merges `system.json` into `~/.config/opencode/opencode.json` (idempotent,
auto-backup `opencode.json.bak-<ts>.json`). Top-level defaults
(`default_agent`, `model`) are last-write-wins across installed systems —
general declares `default_agent` only; reversing declares neither.

Installing any system also installs **global** OpenCode 2 resources so every
project gets them:

- `~/.config/opencode/skills/` — SDD workflow skills (`sdd-specify`, `sdd-plan`,
  `sdd-tasks`, `sdd-implement`, `sdd-converge`)
- `~/.config/opencode/commands/` — SDD slash commands
- `~/.config/opencode/plugins/` — repo plugins (e.g. `guard`)

**Project memory is NOT global.** Each project gets its own `.opencode/` seeded
from `templates/opencode/` — run `.\install.ps1 -InitProject` inside any project
(or with a path) to copy memory seeds (`gotchas.md`, `models.md`, `decisions.md`,
`constitution.md`), `specs/` and `proposals/`. Existing files are never
overwritten unless you pass `-Force`. Agents load these via `instructions[]`
(`.opencode/memory/*.md`) so they reload as the post-compaction baseline.

## Included systems

| system | models | agents | role |
|---|---|---|---|
| `general` | none — inherits your global `model` | gen, gen-explore, gen-coder, gen-analyst | **default** — provider-agnostic general work |
| `reversing` | glmflash-abl, gptoss-abl, qwen38-abl (recommended local Ollama preset, editable) | re, re-explorer, re-coder, re-analyst, re-qa, re-reviewer, re-deep | optional RE/privacy profile |

## Anatomy of a system

```
systems/<name>/
  system.json     # opencode fragment: agents/providers/permissions/compaction/plugins
  models.json     # [{alias, file, pull}] — required Ollama models (optional)
  models/         # referenced Modelfiles (optional)
```

## Tools

- `cli.py` — `agentsys` CLI: `list`/`install`/`remove`/`sync`/`doctor`/`status`/
  `version`/`update`/`uninstall`. `doctor` verifies ollama, opencode2, models,
  config, and flags drift between repo fragments and the installed
  `opencode.json` (fix with `agentsys sync`).
- `tools/bench/` — Ollama multi-model benchmark suite (`bench.py`, `compare.py`, results)
- `tools/opencode-debug/` — session DB inspection + config schema probes

## Persistent memory

Root `AGENTS.md` (read by opencode and devin) → `.opencode/` (native OpenCode 2
dir): `memory/` with `models.md`, `gotchas.md`, `decisions.md` and
`constitution.md` (`memory/` because `.opencode/agent/` is a reserved path).
Update after every notable discovery. It also hosts the SDD workspace:
`specs/<slug>/` (specs driven by `sdd-*` skills in `.opencode/skills/`),
`proposals/` and `commands/`.
