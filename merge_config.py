#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Idempotent deep-merge of config fragments into opencode.json.

Usage:
  python merge_config.py [--config PATH] fragment1.json [fragment2.json ...]

Merge rules:
  - dicts merge recursively (fragment wins on leaf conflicts)
  - lists of scalars: union (deduped, keeps order)
  - lists of dicts (e.g. permissions): appended if not already present
  - a timestamped backup is written next to the target before saving
"""
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


def main() -> int:
    args = sys.argv[1:]
    cfg = DEFAULT_CONFIG
    if args and args[0] == "--config":
        cfg = Path(args[1])
        args = args[2:]
    if not args:
        print("usage: merge_config.py [--config PATH] fragment.json [...]")
        return 2

    base = json.loads(cfg.read_text(encoding="utf-8-sig")) if cfg.exists() else {}
    for f in args:
        frag = json.loads(Path(f).read_text(encoding="utf-8-sig"))
        base = merge(base, frag)

    if cfg.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(cfg, cfg.with_suffix(f".bak-{ts}.json"))
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps(base, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"merged {[Path(f).name for f in args]} -> {cfg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
