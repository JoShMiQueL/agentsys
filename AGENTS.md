# Agent environment — oblitebenchs

Reproducible agentic setup for OpenCode 2 + local Ollama models, focused on
reverse engineering. Read `context/` for memory and decisions before changing things.

## Layout

- `bench.py`, `compare.py`, `prompts.json` — multi-model benchmark suite (Ollama API)
- `install.ps1` — idempotent installer (models + config merge)
- `merge_config.py` — deep-merges JSON fragments into `~/.config/opencode/opencode.json`
- `config/profile_reversing.json` — local-model agent roster (orq/explorer/coder/analyst/deep)
- `config/profile_devin.json` — optional Devin cloud agents (dorq/dexplore/dcoder/danalyst) + `opencode-devin` plugin
- `config/Modelfile.*` — Ollama aliases with baked `num_ctx`
- `dump_db.py`, `dump_msgs.py`, `dump_latest.py`, `dump_session.py` — opencode session DB inspection
- `schema_probe.py`, `schema_perm.py` — fetch live opencode config schema
- `context/` — persistent memory (see below)

## Install / update

```powershell
git pull
.\install.ps1            # models + reversing profile
.\install.ps1 -Devin     # additionally: devin plugin + cloud agents
.\install.ps1 -SkipModels
```

The installer backs up `opencode.json` to `opencode.json.bak-<ts>.json` before every merge. Merges are idempotent — safe to re-run.

## Context / memory

- `context/models.md` — what each model is for and its quirks (read before picking)
- `context/gotchas.md` — failure modes discovered and their fixes
- `context/decisions.md` — architectural decisions and why

When a session uncovers a new quirk or a config change, update these files — they
are the project's memory across reinstalls and machines.

## Gotchas (top hits, details in context/gotchas.md)

- Out-of-workspace file access hangs headless sessions (fixed via `permissions`)
- v2 config uses `agents`+`system` (not deprecated `agent`/`prompt`)
- gpt-oss needs `think:"low"` (think:false does not disable thinking in this build)
- Agent names must be plain English (models hallucinate translations)
- REA is driven via bash `npx rea-agents <cmd>`, NOT MCP (~249K-token catalog)
