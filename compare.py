#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
compare.py — aggregate every results/**/run_*.json into a cross-model report.

Usage:
  python compare.py            # writes results/COMPARE.md and prints it
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def load_runs() -> list[dict]:
    runs = []
    for f in sorted(RESULTS.rglob("run_*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            d["_file"] = str(f.relative_to(ROOT))
            runs.append(d)
        except Exception as e:
            print(f"warn: skipping {f}: {e}", file=sys.stderr)
    return runs


def flatten(runs: list[dict]) -> dict:
    """Dedupe to latest result per (model, config, test_id)."""
    latest: dict[tuple, dict] = {}
    cfgmeta: dict[tuple, dict] = {}
    for run in runs:
        model = run.get("model", "?")
        for cfg, block in (run.get("configs") or {}).items():
            cfgmeta[(model, cfg)] = {k: v for k, v in block.items() if k != "tests"}
            for t in block.get("tests", []):
                latest[(model, cfg, t["id"])] = t
    return {"tests": latest, "cfgmeta": cfgmeta}


def mean_tps(tests: list[dict]) -> float:
    tok = sum(t.get("eval_tokens") or 0 for t in tests)
    dur = sum((t.get("eval_tokens") or 0) / t["eval_tps"] for t in tests if t.get("eval_tps"))
    return round(tok / dur, 1) if dur else 0.0


def main() -> None:
    data = flatten(load_runs())
    latest, cfgmeta = data["tests"], data["cfgmeta"]

    per_cfg: dict[tuple, list] = defaultdict(list)
    for (model, cfg, _tid), t in latest.items():
        per_cfg[(model, cfg)].append(t)

    out = ["# COMPARE — oblitebenchs", ""]

    out += [
        "## Por config",
        "",
        "| model | config | n | pass | fail | loops | th.ovf | eval t/s | VRAM MB |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for (model, cfg), tests in sorted(per_cfg.items()):
        n = len(tests)
        npass = sum(1 for t in tests if t["passed"] is True)
        nfail = sum(1 for t in tests if t["passed"] is False)
        nloop = sum(1 for t in tests if t.get("loop"))
        novf = sum(1 for t in tests if t.get("think_overflow"))
        vram = (cfgmeta.get((model, cfg)) or {}).get("vram_mb", "")
        out.append(
            f"| {model} | {cfg} | {n} | {npass} | {nfail} | {nloop} "
            f"| {novf} | {mean_tps(tests)} | {vram} |"
        )

    # category matrix
    cats = sorted({t.get("category") for t in latest.values() if t.get("category")})
    models = sorted({m for (m, _c, _t) in latest})
    out += ["", "## Pass rate por categoría", "",
            "| model | " + " | ".join(cats) + " |",
            "|---|" + "---|" * len(cats)]
    for m in models:
        cells = []
        for c in cats:
            ts = [t for (mm, _c, _i), t in latest.items()
                  if mm == m and t.get("category") == c]
            valid = [t for t in ts if t["passed"] is not None]
            cells.append(
                f"{sum(1 for t in valid if t['passed'])}/{len(valid)}" if valid else "-"
            )
        out.append(f"| {m} | " + " | ".join(cells) + " |")

    # per-test matrix
    tids = sorted({tid for (_m, _c, tid) in latest})
    out += ["", "## Matrix test × model (último resultado)",
            "", "| test | " + " | ".join(models) + " |",
            "|---|" + "---|" * len(models)]
    mark = {True: "P", False: "**F**", None: "-"}
    for tid in tids:
        cells = []
        for m in models:
            hits = [t for (mm, _c, ii), t in latest.items() if mm == m and ii == tid]
            t = hits[-1] if hits else None
            cells.append(mark[t["passed"]] if t else "·")
        out.append(f"| {tid} | " + " | ".join(cells) + " |")

    # scaling prefill
    out += ["", "## Prefill scaling", "",
            "| model | test | prompt tok | prefill t/s | eval t/s |",
            "|---|---|---|---|---|"]
    for (m, _c, tid), t in sorted(latest.items()):
        if t.get("category") == "scaling":
            out.append(
                f"| {m} | {tid} | {t.get('prompt_tokens','')} "
                f"| {t.get('prefill_tps','')} | {t.get('eval_tps','')} |"
            )

    text = "\n".join(out) + "\n"
    dest = RESULTS / "COMPARE.md"
    dest.write_text(text, encoding="utf-8")
    print(text)
    print(f"-> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
