# Gotchas (OpenCode 2 harness)

Universal harness quirks worth keeping in memory. Add project-specific
entries below as they are discovered.

## Session hangs

- **Out-of-workspace access = eternal hang in headless.** `read`/`glob` on
  paths outside the session dir triggers a permission prompt nobody answers.
  Fix via `permissions` ruleset allowing external_directory/read/glob/grep/bash.
- **`question` tool wedges headless runs.** Prompts forbid it; agents decide alone.
- **Unbounded recursive globs** (e.g. `**/x` over a home dir) stall forever.
  Cap tool calls and demand concrete paths.

## Config schema (v2)

- `agents` + `system` + `model` are correct; `agent`/`prompt`/`small_model`/
  `subagent_depth` are DEPRECATED and silently ignored.
- `permissions` = ordered ruleset `[{action, resource, effect}]`, allow|deny|ask.
- `plugins` (plural) v2; v1 plugins incompatible.

## Models / tool calling

- Models hallucinate tool args and translated agent names. Fixes: English
  agent names, prompts forbid invented fields, orchestrator retries fixing
  only args.
- `agents.*.model` display may show the global default — verify the actual
  model in the session DB if it matters.
- Large MCP servers add their full tool catalog to every session — remove
  unused servers.

## Plugins (v2)

- Dirs under `~/.config/opencode/plugins/<name>/` are auto-discovered — no
  `plugins` key needed in opencode.json.
- A configured `deny` permission rule is FINAL: it short-circuits before
  `permission.hook("evaluate")` runs. To give agents feedback instead of
  silent blocks, keep deny patterns out of `permissions` and let a plugin
  set `effect="deny"` + `message` in the hook.

## Project-specific gotchas

<!-- append discoveries here -->
