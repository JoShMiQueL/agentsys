# Design: durable per-agent overrides + shared-key unmerge fix

Status: design only (no implementation). Author: deep-analysis pass, 2026-10-22.

## Verified facts (from cli.py / merge_config.py / system.json)

- `merge(dst, src)` is a deep merge: dicts recurse, lists union-append, **src wins
  on scalar leaves**. Keys absent from `src` are untouched in `dst`.
- `unmerge(dst, src)`: dict — for each src key, delete `dst[k]` if equal to the
  fragment value, else recurse and drop the key if it becomes `{}`. List —
  remove any item present in `src`.
- `general/system.json` defines **no `model`** on its agents; `reversing`
  defines `model` on all six agents. Both contribute `instructions` and
  `reversing` alone contributes `permissions` + `compaction`.
- `remove(name)` does `unmerge(cfg, frag)` then pops `state["installed"][name]`.
- `cmd_sync` calls `install(n)` per state-tracked system; `install` merges
  `systems/<n>/system.json` into CFG.
- `cmd_uninstall` unmerges every installed/detected system, then
  `shutil.rmtree(INSTALL_DIR)` — anything under `~/.agentsys/` is destroyed.
- `install.ps1` calls `merge_config.py --config <cfg> @frags`; `cli.py` has its
  own copy of `merge`/`unmerge` (duplicated logic).

## Problem 1 — durable overrides

### Why "just edit opencode.json" (option 2) is insufficient

It already works **only for `general`**: the fragment omits `model`, so a
hand-set `agents.gen.model` survives `sync` (merge doesn't touch it) and
`git pull` (opencode.json isn't in the repo). But for `reversing` agents the
fragment *defines* `model` — every `sync`/`install`/`update` overwrites the
user's value. Zero-code survives 2/3 cases; we need all 3.

### Recommended mechanism: single user overlay, merged last

File: **`~/.config/opencode/agentsys-overrides.json`** (same dir as
opencode.json — sits next to what it overrides, survives repo pull AND
`agentsys update`'s INSTALL_DIR wipe; NOT under `~/.agentsys/` because
`cmd_uninstall` rmtree's that and the bootstrap installer wipes `$Dest\*` on
remote reinstall).

Structure: same schema as `system.json` — sparse, additive. Typically:

```json
{
  "agents": {
    "gen-coder": { "model": "ollama/devstral-abl:latest" },
    "re-deep":   { "model": "ollama/qwen38-abl:latest", "options": {"num_ctx": 32768} }
  }
}
```

Any leaf (model, options, permissions additions, even `system`) may be
overridden. Overlay wins over every fragment because it merges last.

Merge order in `cli.py` (one constant `OVERLAY = CFG.parent /
"agentsys-overrides.json"`, one helper `apply_overlay(cfg)`):

- `install()`: `cfg = apply_overlay(merge(load_json(CFG,{}), frag))`
- `remove()`: after unmerge + re-merge of remaining fragments (below), then
  `apply_overlay`
- `cmd_uninstall`: `unmerge(cfg, overlay)` after system unmerges; leave the
  file on disk (user data) but print a note.
- `install.ps1`: append `$cfgDir\agentsys-overrides.json` to `@frags` if it
  exists, so the PS bootstrap path behaves identically.

Missing file = no-op (`load_json(OVERLAY, {})`). Idempotent: applying it N
times during `sync` is safe.

## Problem 2 — shared-key stripping on `remove`

`unmerge` deletes a dst key when it equals the fragment's value, so removing
`reversing` strips `instructions` even though `general` also contributes it.

### Fix: re-merge leftovers (order matters)

```python
def remove(name):
    # 1. update state FIRST so the removed system isn't re-applied
    state["installed"].pop(name, None); save_json(STATE, state)
    # 2. unmerge the removed fragment
    cfg = unmerge(load_json(CFG, {}), frag)
    # 3. re-apply every REMAINING installed system's fragment
    for other in state["installed"]:
        cfg = merge(cfg, load_json(SYSTEMS / other / "system.json", {}))
    # 4. overlay always last
    cfg = apply_overlay(cfg)
    save_json(CFG, cfg)
```

Shared keys are restored because a surviving contributor re-adds them.
Verified for dict leaves AND list items (`instructions` union re-adds the
glob; `permissions` items re-append). `default_agent` is scalar — if the
removed system owned it and no survivor defines it, it is correctly deleted.

## Edge cases

- **Residue stubs**: `unmerge` keeps keys the fragment didn't set. With an
  override `agents.gen.model`, `remove general` leaves `agents.gen = {model}`
  — the agent still exists. Overlay intentionally owns those keys; the same
  stub also survives `uninstall`. Document: removing a system does not remove
  agents you overrode; delete the overlay entry too (or accept stubs — an
  agent with only `model` inherits nothing else but still registers).
- **Lists are append-only**: overlay can add permission rules but cannot
  remove one a fragment contributed (delete requires manual opencode.json
  edit + it returns on next sync — documented limitation; a future `"-name"`
  subtraction syntax is out of scope).
- **doctor drift**: agent `system`-prompt check (cli.py:233) will flag a
  user-overridden prompt as drift. doctor should also load the overlay and
  skip keys present there.
- **Sync after pull**: if a pulled fragment renames an agent, overlay entries
  for the old name become inert stubs — acceptable, user cleans up.
- **merge_config.py stays generic**: keep it overlay-agnostic; only
  `install.ps1` appends the overlay path to `@frags`.

## Alternatives rejected

- `systems/<name>/system.local.json` in-repo: gitignored files still tie user
  config to the repo lifecycle; doesn't cover "one file for all systems"
  cleanly; update/reinstall flows in cli.py reference SYSTEMS dir — same
  solution strictly worse placed.
- Overlay under `~/.agentsys/`: destroyed by `cmd_uninstall` and by the
  irm-bootstrap `Remove-Item "$Dest\*"` on reinstall. Config-dir survives both.
