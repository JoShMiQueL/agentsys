# agentsys — colección instalable de sistemas de agentes para OpenCode 2

Cada carpeta en `systems/` es un sistema completo e instalable con un comando.
Añadir uno nuevo = crear `systems/<nombre>/system.json` (+ `models.json` opcional).

## Install

```powershell
# bun-style, no clone needed — installs everything:
powershell -c "irm https://raw.githubusercontent.com/JoShMiQueL/agentsys/master/install.ps1 | iex"

# or locally after clone:
.\install.ps1 -Systems reversing,devin [-SkipModels] [-NoDeps]
```

Fully automatic: missing deps (Python 3.11, Ollama, Node/opencode2) are
installed via `winget`/`npm`. Use `-NoDeps` to fail instead of auto-installing.
`install.ps1` creates Ollama aliases declared in `models.json` and merges
`system.json` into `~/.config/opencode/opencode.json` (idempotent, auto-backup
`opencode.json.bak-<ts>.json`).

## Sistemas incluidos

| sistema | modelos | agentes |
|---|---|---|
| `reversing` | glmflash-abl, gptoss-abl, qwen38-abl (Ollama locales) | orq, explorer, coder, analyst, deep |
| `devin` | swe-2-* cloud (plugin `opencode-devin`) | dorq, dexplore, dcoder, danalyst |

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

`AGENTS.md` en raíz (leído por opencode y devin) → `context/`:
`models.md`, `gotchas.md`, `decisions.md`. Actualizar tras cada descubrimiento.
