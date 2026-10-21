# oblitebenchs — reproducible agent env for OpenCode 2 + Ollama

Agentic reversing setup: local abliterated models + orchestrated subagents,
packaged for one-command reinstall on any machine.

## Install

```powershell
git clone <repo> oblitebenchs; cd oblitebenchs
.\install.ps1            # ollama aliases + reversing profile
.\install.ps1 -Devin     # + devin plugin (swe-2-* cloud agents)
.\install.ps1 -SkipModels
```

Requires: Ollama, Python 3.11+, opencode2 (`npm i -g @opencode-ai/cli@next`).

## What it installs

**Ollama aliases** (baked `num_ctx`, zero extra disk):
`glmflash-abl` (16k), `gptoss-abl` (16k), `qwen38-abl` (8k)

**Agents** merged into `~/.config/opencode/opencode.json` (idempotent, auto-backup):

| reversing (local) | devin (cloud, optional) | role |
|---|---|---|
| orq | dorq | primary orchestrator |
| explorer | dexplore | read-only research |
| coder | dcoder | implementation |
| analyst | danalyst | technical/RE analysis |
| deep | — | 27B escalation |

Plus permissive `permissions` ruleset (no headless hangs) and `compaction.auto`.

## Benchmark suite

```powershell
python bench.py --phase all --model <m>   # perf/quality/think/scaling
python compare.py                         # -> results/COMPARE.md
```

## Memory

`AGENTS.md` (index, read by opencode+devin) → `context/models.md`,
`context/gotchas.md`, `context/decisions.md`. Update after discoveries —
this is the project's persistent memory.

## Design notes

- REA driven via bash `npx rea-agents <cmd>`, not MCP (249K-token catalog)
- One resident model, N logical agents — weights shared, contexts separate
- Artifact-first: workers write to disk, report compact paths
- See `context/decisions.md` for the full reasoning
