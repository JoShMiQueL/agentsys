#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Idempotent deep-merge of config fragments into opencode.json.

Usage:
  python merge_config.py [--config PATH] [--dry-run] fragment1.json [fragment2.json ...]

Merge rules:
  - dicts merge recursively (fragment wins on leaf conflicts)
  - lists of scalars: union (deduped, keeps order)
  - lists of dicts (e.g. permissions): appended if not already present
  - a timestamped backup is written next to the target before saving
  - --dry-run: print a compact diff summary, write nothing (no backup either)
"""
import copy
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_CONFIG = Path.home() / ".config" / "opencode" / "opencode.json"


def merge(dst, src):
    if isinstance(dst, dict) and isinstance(src, dict):
        for k, v in src.items():
            dst[k] = merge(dst.get(k), v)
        return dst
    if isinstance(dst, list) and isinstance(src, list):
        for item in src:
            if item not in dst:
                dst.append(item)
        return dst
    return src  # fragment wins


def diff_summary(before, after):
    """Compact ~15-line diff of agents + top-level keys."""
    tag = "[dry]"
    ba, aa = before.get("agents") or {}, after.get("agents") or {}
    added = sorted(set(aa) - set(ba))
    removed = sorted(set(ba) - set(aa))
    changed = sorted(a for a in set(ba) & set(aa) if ba[a] != aa[a])
    if added:
        print(f"{tag} agents added ({len(added)}): {', '.join(added)}")
    if removed:
        print(f"{tag} agents removed ({len(removed)}): {', '.join(removed)}")
    for a in changed[:5]:
        bks = ba[a] if isinstance(ba[a], dict) else {}
        aks = aa[a] if isinstance(aa[a], dict) else {}
        keys = sorted(k for k in set(bks) | set(aks) if bks.get(k) != aks.get(k))
        print(f"{tag} agent {a} changed keys: {', '.join(keys)}")
    if len(changed) > 5:
        print(f"{tag} ... and {len(changed) - 5} more changed agent(s)")
    top = sorted(k for k in set(before) | set(after)
                 if k != "agents" and before.get(k) != after.get(k))
    for k in top[:8]:
        bv, av = before.get(k), after.get(k)
        fmt = lambda v: (f"{len(v)} item(s)" if isinstance(v, list)
                         else ("{...}" if isinstance(v, dict) else v))
        print(f"{tag} {k}: {fmt(bv)} -> {fmt(av)}")
    if len(top) > 8:
        print(f"{tag} ... and {len(top) - 8} more top-level key(s)")
    if before == after:
        print(f"{tag} no changes")


def main() -> int:
    args = sys.argv[1:]
    cfg = DEFAULT_CONFIG
    dry = False
    if "--dry-run" in args:
        dry = True
        args.remove("--dry-run")
    if args and args[0] == "--config":
        cfg = Path(args[1])
        args = args[2:]
    if not args:
        print("usage: merge_config.py [--config PATH] [--dry-run] fragment.json [...]")
        return 2

    base = json.loads(cfg.read_text(encoding="utf-8-sig")) if cfg.exists() else {}
    before = copy.deepcopy(base)
    for f in args:
        frag = json.loads(Path(f).read_text(encoding="utf-8-sig"))
        base = merge(base, frag)

    if dry:
        print(f"[dry] merge {len(args)} fragment(s) -> {cfg}")
        diff_summary(before, base)
        return 0
    if cfg.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(cfg, cfg.with_suffix(f".bak-{ts}.json"))
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps(base, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"merged {[Path(f).name for f in args]} -> {cfg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
