#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Smoke test for agentsys cli.py — exits non-zero on failure.

Runs read-only commands + dry-run install/remove and validates output
markers. Verifies --dry-run leaves opencode.json untouched (hash check).
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli.py"
CFG = Path.home() / ".config" / "opencode" / "opencode.json"

fails = []


def run(*args):
    p = subprocess.run([sys.executable, str(CLI), *args],
                       capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


def check(name, cond, detail=""):
    status = "ok" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail.strip()[:100]}" if not cond else ""))
    if not cond:
        fails.append(name)


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


print("== agentsys smoke ==")

rc, out = run("list")
check("list rc=0", rc == 0)
check("list shows general", "general" in out)

rc, out = run("status")
check("status rc=0", rc == 0)
check("status shows default_agent", "default_agent:" in out)

rc, out = run("doctor")
check("doctor rc=0", rc == 0)
check("doctor verdict", "doctor:" in out)

# dry-run install: must print diff, must not touch CFG
h0 = sha(CFG)
rc, out = run("install", "general", "--dry-run")
check("install --dry-run rc=0", rc == 0, out)
check("install --dry-run prints [dry]", "[dry]" in out)
check("install --dry-run diff summary", "diff summary" in out)
check("opencode.json unchanged", sha(CFG) == h0)
check("install --dry-run wrote nothing", "[ok]" not in out)

# -n alias on remove
rc, out = run("remove", "reversing", "-n")
check("remove -n rc=0", rc == 0, out)
check("remove -n prints [dry] or err", "[dry]" in out or "[err]" in out)
check("opencode.json still unchanged", sha(CFG) == h0)

if fails:
    print(f"\nsmoke: {len(fails)} FAILURE(S)")
    sys.exit(1)
print("\nsmoke: all checks passed")
