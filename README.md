# agentsys — colección instalable de sistemas de agentes para OpenCode 2

Cada carpeta en `systems/` es un sistema completo e instalable con un comando.
Añadir uno nuevo = crear `systems/<nombre>/system.json` (+ `models.json` opcional).

## Install

```powershell
# bun-style, no clone needed — installs everything:
powershell -c "irm https://raw.githubusercontent.com/JoShMiQueL/agentsys/master/install.ps1 | iex"

# or locally after clone:
.\install.ps1 -Systems reversing,devin [-SkipModels] [-NoDeps]

# seed .opencode/ (memory, specs, proposals) into a project:
.\install.ps1 -InitProject <path-to-project> [-Force]
```

Fully automatic: missing deps (Python 3.11, Ollama, Node/opencode2) are
installed via `winget`/`npm`. Use `-NoDeps` to fail instead of auto-installing.
`install.ps1` creates Ollama aliases declared in `models.json` and merges
`system.json` into `~/.config/opencode/opencode.json` (idempotent, auto-backup
`opencode.json.bak-<ts>.json`).

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

## Sistemas incluidos

| sistema | modelos | agentes |
|---|---|---|
| `reversing` | glmflash-abl, gptoss-abl, qwen38-abl (Ollama locales) | re, re-explorer, re-coder, re-analyst, re-qa, re-reviewer, re-deep |
| `devin` | swe-2-* cloud (plugin `opencode-devin`) | gen, gen-explore, gen-coder, gen-analyst |

## Anatomía de un sistema

```
systems/<nombre>/
  system.json     # fragmento opencode: agents/providers/permissions/compaction/plugins
  models.json     # [{alias, file, pull}] — modelos Ollama requeridos (opcional)
  models/         # Modelfiles referenciados (opcional)
```

## Tools

- `tools/bench/` — suite de benchmarks Ollama multi-modelo (`bench.py`, `compare.py`, resultados)
- `tools/opencode-debug/` — inspección de sesiones DB y schema probing

## Memoria persistente

`AGENTS.md` en raíz (leído por opencode y devin) → `.opencode/` (dir nativo de
OpenCode 2): `memory/` con `models.md`, `gotchas.md`, `decisions.md` y
`constitution.md` (se usa `memory/` porque `.opencode/agent/` es ruta reservada).
Actualizar tras cada descubrimiento. También aloja el workspace SDD:
`specs/<slug>/` (specs dirigidas por skills `sdd-*` en `.opencode/skills/`),
`proposals/` y `commands/`.
