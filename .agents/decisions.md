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
