# agent-systems — colección instalable de sistemas de agentes para OpenCode 2

Cada carpeta en `systems/` es un sistema completo e instalable con un comando.
Añadir uno nuevo = crear `systems/<nombre>/system.json` (+ `models.json` opcional).

## Install

```powershell
git clone <repo>; cd agent-systems
.\install.ps1                          # sistema 'reversing' (default)
.\install.ps1 -Systems reversing,devin # varios a la vez
.\install.ps1 -Systems devin -SkipModels
```

Requiere: Ollama, Python 3.11+, opencode2 (`npm i -g @opencode-ai/cli@next`).
`install.ps1` crea aliases de Ollama declarados en `models.json` y mergea
`system.json` en `~/.config/opencode/opencode.json` (idempotente, backup
automático `opencode.json.bak-<ts>.json`).

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
