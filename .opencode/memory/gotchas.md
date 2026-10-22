# Gotchas discovered (opencode2 + local models)

## Session hangs

- **Out-of-workspace access = eternal hang in headless.** `read`/`glob` on
  paths outside the session dir triggers a permission prompt nobody answers.
  Fixed by `permissions` ruleset allowing external_directory/read/glob/grep/bash.
- **`question` tool wedges headless runs.** Prompts forbid it; agents decide alone.
- **Unbounded recursive globs** (e.g. `**/x` over `C:\Users\...`) stall forever.
  explorer prompt caps tool calls and demands concrete paths.

## Config schema (v2)

- `agents` + `system` + `model` are correct; `agent`/`prompt`/`small_model`/
  `subagent_depth` are DEPRECATED and silently ignored.
- `Config.AgentEncoded.options` passes extra request body fields (used for `think:"low"`).
- `permissions` = ordered ruleset `[{action, resource, effect}]`, allow|deny|ask.
- `plugins` (plural) v2; v1 plugins incompatible.

## Models / tool calling

- Models hallucinate tool args (`sessionID` on `subagent`, agent name
  `explorer` when defined as `explorador`). Fixes: English agent names,
  prompt forbids invented fields, orchestrator retries fixing only args.
- `agents.*.model` display may show the global default — verify actual model
  in session_v2 DB if it matters.
- MCP `chrome-devtools` adds 32 tool schemas to every session — remove if unused.

## Plugins (v2)
- Dirs under `~/.config/opencode/plugins/<name>/` are auto-discovered — no
  `plugins` key needed in opencode.json.
- A configured `deny` permission rule is FINAL: it short-circuits before
  `permission.hook("evaluate")` runs. To give agents feedback instead of silent
  blocks, keep deny patterns out of `permissions` and let a plugin (see
  `plugins/guard`) set `event.effect="deny"` + `event.message` in the hook —
  the message reaches the model as a Tool.Error.
- `merge_config.py` only APPENDS to list-of-dicts (permissions): removing a
  deny rule from a system.json fragment does NOT remove it from the installed
  opencode.json — clean it manually.

## Merge / unmerge (cli.py)

- **Snapshot-based remove = zero residue.** `install()` stores the merged
  fragment in `agent-systems.json` (`installed.<name>.fragment`); `remove()`
  unmerges THAT snapshot (not whatever system.json says now), hard-deletes
  every agent the fragment defined (plain `unmerge` leaves stubs when a leaf
  diverged), and force-drops `default_agent`/`model` the fragment owned.
  Survivor fragments are re-merged to restore shared keys (`instructions`),
  then the overlay. Legacy state without `fragment` falls back to live
  system.json. Overlay-covered agents and diverged user values the fragment
  never owned intentionally survive `remove` — by design.
- **Unmerge-only loses shared keys.** `unmerge` deletes a dst key when it
  equals the fragment's value, so `remove reversing` stripped `instructions`
  even though `general` also contributes it. Fixed: `remove()` pops state
  FIRST, unmerges, then re-merges every *remaining* installed system's
  fragment (survivors re-add shared keys), then applies the overlay.
- **User overlay merged last.** `~/.config/opencode/agentsys-overrides.json`
  wins over all fragments; applied in install/remove/uninstall paths and in
  install.ps1's `@frags`. Removing a system leaves agent stubs for
  overlay-overridden agents — that's by design (delete the overlay entry).
