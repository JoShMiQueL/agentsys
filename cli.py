#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""agentsys — manage opencode agent systems from this repo.

Commands:
  list                 systems available in the repo + install state
  install <name>...    pull/create ollama models + merge system.json
  remove <name>...     uninstall a system (agents/permissions/plugins/defaults)
  sync                 re-apply every installed system (after git pull)
  doctor               verify environment: ollama, opencode2, models, config
  version              installed version + update check
  status               live opencode.json vs installed systems
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
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


def split_agents(agents: dict) -> tuple[list, list]:
    prim = sorted(a for a, v in agents.items() if (v.get("mode") or "primary") in ("primary", "all"))
    subs = sorted(a for a, v in agents.items() if v.get("mode") == "subagent")
    return prim, subs


def cmd_list():
    state = load_json(STATE, {"installed": {}})["installed"]
    cfg = load_json(CFG, {})
    cfg_agents = set((cfg.get("agents") or {}).keys())
    for name in system_dirs():
        frag = load_json(SYSTEMS / name / "system.json", {})
        agents = frag.get("agents") or {}
        prim, subs = split_agents(agents)
        live = all(a in cfg_agents for a in agents)
        st = "installed" if name in state or live else "available"
        print(f"{name} [{st}]")
        for a in prim:
            print(f"  primary:  {a}  ({agents[a].get('model','')})")
        for a in subs:
            print(f"  subagent: {a}  ({agents[a].get('model','')})")


def cmd_status():
    cfg = load_json(CFG, {})
    agents = cfg.get("agents") or {}
    prim, subs = split_agents(agents)
    print("default_agent:", cfg.get("default_agent"), "| model:", cfg.get("model"))
    print("primaries:", ", ".join(prim) or "(none)")
    print("subagents:", ", ".join(subs) or "(none)")
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


REPO = "JoShMiQueL/agentsys"


def remote_tag() -> str | None:
    """Latest git tag on the repo (= newest release), or None."""
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/tags",
            headers={"User-Agent": "agentsys"})
        tags = json.load(urllib.request.urlopen(req, timeout=10))
        return tags[0]["name"] if tags else None
    except Exception:
        return None


def local_version() -> str | None:
    f = ROOT / "VERSION"
    if f.exists():
        return f.read_text().strip()
    return None


def _ver(s: str) -> tuple:
    """'v0.2.10' -> (0, 2, 10) for correct ordering."""
    return tuple(int(x) for x in re.findall(r"\d+", s or ""))


def cmd_update():
    remote = remote_tag()
    if not remote:
        print("cannot reach github — check connectivity")
        return
    local = local_version()
    if local == remote:
        print(f"up to date ({remote})")
        return
    print(f"update available: {local or '?'} -> {remote}")
    if (ROOT / ".git").exists():
        # dev checkout: keep git semantics
        subprocess.run(["git", "-C", str(ROOT), "fetch", "--tags", "-f"], check=True)
        subprocess.run(["git", "-C", str(ROOT), "checkout", remote], check=True)
    else:
        print("applying tag archive...")
        data = urllib.request.urlopen(urllib.request.Request(
            f"https://github.com/{REPO}/archive/refs/tags/{remote}.zip",
            headers={"User-Agent": "agentsys"}), timeout=60).read()
        zf = zipfile.ZipFile(io.BytesIO(data))
        new_files = {n.split("/", 1)[1] for n in zf.namelist()
                     if "/" in n and n.split("/", 1)[1]}
        tmp = Path(tempfile.mkdtemp())
        zf.extractall(tmp)
        src = next(tmp.iterdir())
        # managed install dir: remove files that no longer exist in the release
        for p in ROOT.rglob("*"):
            rel = p.relative_to(ROOT).as_posix()
            if p.is_file() and rel not in new_files and rel != "VERSION":
                try:
                    p.unlink()
                except OSError:
                    pass
        shutil.copytree(src, ROOT, dirs_exist_ok=True)
        shutil.rmtree(tmp, ignore_errors=True)
    (ROOT / "VERSION").write_text(remote + "\n")
    # refresh notice cache so it doesn't nag about a version we just installed
    st = load_json(STATE, {"installed": {}})
    st["update_check"] = {"at": datetime.now().timestamp(), "latest": remote}
    save_json(STATE, st)
    print("re-applying installed systems...")
    cmd_sync()


def cmd_version():
    local = local_version() or "dev checkout"
    remote = remote_tag()
    print(f"agentsys {local}")
    if remote and _ver(remote) > _ver(local):
        print(f"update available: {local} -> {remote} - run: agentsys update")
    elif remote and local == remote:
        print("up to date")


def notice_update():
    """Cached (1h) 'update available' nudge appended after any command."""
    try:
        st = load_json(STATE, {"installed": {}})
        cache = st.get("update_check") or {}
        now = datetime.now().timestamp()
        if now - cache.get("at", 0) > 3600:
            t = remote_tag()
            if t:
                cache = {"at": now, "latest": t}
                st["update_check"] = cache
                save_json(STATE, st)
        latest = cache.get("latest")
        local = local_version()
        if latest and local and _ver(latest) > _ver(local):
            if sys.platform == "win32":
                os.system("")  # enable ANSI on Windows console
            print(f"\n\033[33m[agentsys] new version {latest} (you have {local})"
                  f" - run: agentsys update\033[0m")
    except Exception:
        pass


INSTALL_DIR = Path.home() / ".agentsys"


def _unpath():
    """Remove INSTALL_DIR/bin from PATH (winreg on Windows, rc files on unix)."""
    b = str(INSTALL_DIR / "bin").lower()
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                                 winreg.KEY_ALL_ACCESS)
            path = winreg.QueryValueEx(key, "Path")[0]
            keep = [p for p in path.split(";") if p and b not in p.lower()]
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(keep))
            winreg.CloseKey(key)
        except Exception:
            pass
    else:
        for rc in [Path.home() / f for f in (".bashrc", ".zshrc", ".profile")]:
            if rc.exists():
                lines = [l for l in rc.read_text().splitlines()
                         if ".agentsys/bin" not in l]
                rc.write_text("\n".join(lines) + "\n")


def cmd_uninstall():
    """Remove every installed system + CLI itself. Ollama models untouched."""
    cfg = load_json(CFG, {})
    cfg_agents = cfg.get("agents") or {}
    names = set((load_json(STATE, {"installed": {}})["installed"]).keys())
    # also detect systems whose agents are present but not state-tracked
    for n in system_dirs():
        frag = load_json(SYSTEMS / n / "system.json", {})
        ags = (frag.get("agents") or {}).keys()
        if ags and all(a in cfg_agents for a in ags):
            names.add(n)
    for name in names:
        frag = SYSTEMS / name / "system.json"
        if frag.exists():
            cfg = unmerge(cfg, load_json(frag, {}))
        print(f"  [unmerged] {name}")
    backup()
    save_json(CFG, cfg)
    _unpath()
    if STATE.exists():
        STATE.unlink()
    shutil.rmtree(INSTALL_DIR, ignore_errors=True)
    if INSTALL_DIR.exists():
        print(f"  [warn] could not fully remove {INSTALL_DIR} — delete manually")
    print("uninstalled. Ollama models kept (remove manually: ollama rm <alias>)")


USAGE = __doc__


def _dispatch(cmd: str, rest: list) -> int:
    if cmd == "install":
        return 0 if all(install(n) for n in rest) else 1
    if cmd == "remove":
        return 0 if all(remove(n) for n in rest) else 1
    if cmd == "uninstall":
        cmd_uninstall(); return 0
    if cmd == "list":
        cmd_list(); return 0
    if cmd == "sync":
        cmd_sync(); return 0
    if cmd == "status":
        cmd_status(); return 0
    if cmd == "update":
        cmd_update(); return 0
    if cmd == "version":
        cmd_version(); return 0
    if cmd == "doctor":
        cmd_doctor(); return 0
    print(USAGE)
    return 2


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(f"agentsys {local_version() or 'dev checkout'}")
        print(USAGE)
        notice_update()   # post-hook: runs on EVERY command path
        return 0
    cmd, rest = args[0], args[1:]
    rc = _dispatch(cmd, rest)
    if cmd != "update":
        notice_update()
    return rc


if __name__ == "__main__":
    sys.exit(main())
