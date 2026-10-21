#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""agentsys — manage opencode agent systems from this repo.

Commands:
  list                 systems available in the repo + install state
  install <name>...    pull/create ollama models + merge system.json
  remove <name>...     uninstall a system (agents/permissions/plugins/defaults)
  sync                 re-apply every installed system (after git pull)
  doctor               verify environment: ollama, opencode2, models, config
  status               live opencode.json vs installed systems
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SYSTEMS = ROOT / "systems"
CFG = Path.home() / ".config" / "opencode" / "opencode.json"
STATE = Path.home() / ".config" / "opencode" / "agent-systems.json"


def load_json(p: Path, default):
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8-sig"))
    return default


def save_json(p: Path, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge(dst, src):
    if isinstance(dst, dict) and isinstance(src, dict):
        for k, v in src.items():
            dst[k] = merge(dst.get(k), v)
        return dst
    if isinstance(dst, list) and isinstance(src, list):
        for i in src:
            if i not in dst:
                dst.append(i)
        return dst
    return src


def unmerge(dst, src):
    """Remove what src contributed (dicts by key, lists by value)."""
    if isinstance(dst, dict) and isinstance(src, dict):
        for k, v in src.items():
            if k in dst:
                if dst[k] == v:
                    del dst[k]
                else:
                    unmerge(dst[k], v)
                    if dst.get(k) == {}:
                        del dst[k]
        return dst
    if isinstance(dst, list) and isinstance(src, list):
        dst[:] = [i for i in dst if i not in src]
        return dst
    return dst


def backup():
    if CFG.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(CFG, CFG.with_suffix(f".bak-{ts}.json"))


def ollama_models() -> set[str]:
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=15)
        return {l.split()[0] for l in out.stdout.splitlines()[1:] if l.strip()}
    except Exception:
        return set()


def system_dirs():
    return sorted(p.name for p in SYSTEMS.iterdir() if (p / "system.json").exists())


def install(name: str) -> bool:
    sdir = SYSTEMS / name
    frag_path = sdir / "system.json"
    if not frag_path.exists():
        print(f"  [err] system '{name}' not found")
        return False

    have = ollama_models()
    mfile = sdir / "models.json"
    if mfile.exists():
        for m in json.loads(mfile.read_text(encoding="utf-8"))["models"]:
            alias = m["alias"] + ":latest"
            if alias in have:
                print(f"  [skip] {alias}")
                continue
            if m["pull"] not in have:
                print(f"  [pull] {m['pull']}")
                subprocess.run(["ollama", "pull", m["pull"]], check=True)
            print(f"  [create] {m['alias']}")
            mf = sdir / "models" / m["file"]
            subprocess.run(["ollama", "create", m["alias"], "-f", str(mf)], check=True,
                           capture_output=True)

    backup()
    cfg = merge(load_json(CFG, {}), load_json(frag_path, {}))
    save_json(CFG, cfg)

    state = load_json(STATE, {"installed": {}})
    state["installed"][name] = {"at": datetime.now().isoformat()}
    save_json(STATE, state)
    print(f"  [ok] {name} installed")
    return True


def remove(name: str) -> bool:
    sdir = SYSTEMS / name
    frag_path = sdir / "system.json"
    if not frag_path.exists():
        print(f"  [err] system '{name}' not found")
        return False
    backup()
    cfg = unmerge(load_json(CFG, {}), load_json(frag_path, {}))
    save_json(CFG, cfg)
    state = load_json(STATE, {"installed": {}})
    state["installed"].pop(name, None)
    save_json(STATE, state)
    print(f"  [ok] {name} removed")
    return True


def cmd_list():
    state = load_json(STATE, {"installed": {}})["installed"]
    cfg = load_json(CFG, {})
    cfg_agents = set((cfg.get("agents") or {}).keys())
    print(f"{'system':<14} {'state':<12} agents")
    for name in system_dirs():
        frag = load_json(SYSTEMS / name / "system.json", {})
        ags = sorted((frag.get("agents") or {}).keys())
        live = all(a in cfg_agents for a in ags)
        st = "installed" if name in state or live else "available"
        print(f"{name:<14} {st:<12} {', '.join(ags)}")


def cmd_status():
    cfg = load_json(CFG, {})
    print("default_agent:", cfg.get("default_agent"), "| model:", cfg.get("model"))
    print("agents:", ", ".join(sorted((cfg.get("agents") or {}).keys())) or "(none)")
    print("plugins:", cfg.get("plugins"))
    print("permissions rules:", len(cfg.get("permissions") or []))


def cmd_sync():
    state = load_json(STATE, {"installed": {}})
    names = list(state["installed"].keys()) or [n for n in system_dirs()
                                               if all(a in (load_json(CFG, {}).get("agents") or {})
                                                      for a in (load_json(SYSTEMS / n / "system.json", {})
                                                                .get("agents") or {}))]
    if not names:
        print("nothing installed")
        return
    for n in names:
        install(n)


def cmd_doctor():
    ok = True
    def chk(name, good, extra=""):
        nonlocal ok
        ok &= good
        print(f"  [{'ok' if good else 'FAIL'}] {name} {extra}")
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        chk("ollama api", True)
    except Exception:
        chk("ollama api", False, "(not reachable at :11434)")
    chk("opencode2", bool(shutil.which("opencode2")))
    chk("config", CFG.exists(), str(CFG))
    have = ollama_models()
    for name in system_dirs():
        sdir = SYSTEMS / name
        if not (sdir / "models.json").exists():
            continue
        for m in json.loads((sdir / "models.json").read_text())["models"]:
            chk(f"model {m['alias']}", m["alias"] + ":latest" in have)
    cfg = load_json(CFG, {})
    for name in system_dirs():
        frag = load_json(SYSTEMS / name / "system.json", {})
        for a in (frag.get("agents") or {}):
            present = a in (cfg.get("agents") or {})
            state = load_json(STATE, {"installed": {}})["installed"]
            want = name in state
            chk(f"agent {a} ({name})", present or not want)
    print("doctor:", "healthy" if ok else "issues found")


USAGE = __doc__


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    cmd, rest = args[0], args[1:]
    if cmd == "install":
        return 0 if all(install(n) for n in rest) else 1
    if cmd == "remove":
        return 0 if all(remove(n) for n in rest) else 1
    if cmd == "list":
        cmd_list(); return 0
    if cmd == "sync":
        cmd_sync(); return 0
    if cmd == "status":
        cmd_status(); return 0
    if cmd == "doctor":
        cmd_doctor(); return 0
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
