# agentsys — installable agent collections for OpenCode 2

Multiple systems coexist safely: each is a named set of agents merged into
`~/.config/opencode/opencode.json`. No collisions — agents are namespaced
(`re`/`explorer`/`coder`/`analyst`/`deep` vs `gen`/`dexplore`/`dcoder`/`danalyst`)
and each primary knows its own roster by exact name.

Read `context/` for persistent memory before changing anything.

## Layout

- `systems/<name>/system.json` — config fragment (agents/providers/permissions/defaults)
- `systems/<name>/models.json` + `models/` — Ollama aliases required (optional)
- `install.ps1` — idempotent installer (`-Systems a,b`, `-SkipModels`)
- `merge_config.py` — deep-merge with auto-backup of opencode.json
- `tools/bench/` — Ollama multi-model benchmark suite
- `tools/opencode-debug/` — session DB inspection + config schema probes
- `context/` — project memory (models.md, gotchas.md, decisions.md)

## Install / sync

```powershell
git pull
.\install.ps1                          # reversing system (default)
.\install.ps1 -Systems reversing,devin # several systems side by side
.\install.ps1 -SkipModels
```

Top-level defaults (`model`, `default_agent`) are last-write-wins across
systems; each primary agent still carries its own model. Switch systems by
choosing the agent (`/agent re` or `opencode2 run --agent re`).

## Hard-won rules (details in context/gotchas.md)

- v2 schema: `agents`+`system`+`model` (deprecated `agent`/`prompt` are ignored)
- gpt-oss-abliterated requires `think:"low"`; `think:false` does not disable thinking
- Headless hangs come from out-of-workspace permission prompts — fixed via `permissions`
- Agent names stay English; models hallucinate translated names
- REA is driven via bash `npx rea-agents <cmd>`, NOT MCP (~249K-token catalog)
