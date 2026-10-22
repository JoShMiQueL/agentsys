#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""agentsys — manage opencode agent systems from this repo.

Commands:
  list                 systems available in the repo + install state
  install <name>...    pull/create ollama models + merge system.json
                       (--dry-run / -n: compute + show diff, write nothing)
  remove <name>...     uninstall a system (agents/permissions/plugins/defaults)
                       (--dry-run / -n: compute + show diff, write nothing)
  sync                 re-apply every installed system (after git pull)
  doctor               verify environment: ollama, opencode2, models, config
  version              installed version + update check
  status               live opencode.json vs installed systems
"""
from __future__ import annotations

import copy
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
# User overrides overlay: lives next to opencode.json (NOT under ~/.agentsys,
# which cmd_uninstall wipes). Merged LAST so it always wins over fragments.
OVERLAY = CFG.parent / "agentsys-overrides.json"


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


def apply_overlay(cfg):
    """Deep-merge the user overrides overlay into cfg. Missing file = no-op."""
    return merge(cfg, load_json(OVERLAY, {}))


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


def _diff_summary(before: dict, after: dict, name: str, overlay_used: bool):
    """Compact ~15-line diff of what an install/remove would do to opencode.json."""
    tag = "[dry]"
    ba, aa = before.get("agents") or {}, after.get("agents") or {}
    added = sorted(set(aa) - set(ba))
    removed = sorted(set(ba) - set(aa))
    changed = sorted(a for a in set(ba) & set(aa) if ba[a] != aa[a])
    print(f"{tag} {name} - opencode.json diff summary")
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
    for k in ("default_agent", "model"):
        if before.get(k) != after.get(k):
            print(f"{tag} {k}: {before.get(k)} -> {after.get(k)}")
    bi, ai = before.get("instructions") or [], after.get("instructions") or []
    if bi != ai:
        print(f"{tag} instructions: {len(bi)} -> {len(ai)} item(s)")
    bp, ap = len(before.get("permissions") or []), len(after.get("permissions") or [])
    if bp != ap:
        print(f"{tag} permissions: {bp} -> {ap} rule(s)")
    print(f"{tag} overlay: {'applied' if overlay_used else 'not present'}")
    if not (added or removed or changed) and before == after:
        print(f"{tag} no changes")


def install(name: str, dry: bool = False) -> bool:
    sdir = SYSTEMS / name
    frag_path = sdir / "system.json"
    if not frag_path.exists():
        print(f"  [err] system '{name}' not found")
        return False

    mfile = sdir / "models.json"
    if mfile.exists():
        models = json.loads(mfile.read_text(encoding="utf-8"))["models"]
        if dry:
            print(f"  [dry] would create/pull {len(models)} model(s): "
                  + ", ".join(m["alias"] for m in models))
        elif not shutil.which("ollama"):
            print("  [warn] ollama not on PATH — skipping model setup")
        else:
            have = ollama_models()
            for m in models:
                alias = m["alias"] + ":latest"
                if alias in have:
                    print(f"  [skip] {alias}")
                    continue
                if m["pull"] not in have:
                    print(f"  [pull] {m['pull']}")
                    subprocess.run(["ollama", "pull", m["pull"]], check=True)
                print(f"  [create] {m['alias']}")
                mf = sdir / "models" / m["file"]
                subprocess.run(["ollama", "create", m["alias"], "-f", str(mf)],
                               check=True, capture_output=True)

    frag = load_json(frag_path, {})
    before = load_json(CFG, {})
    cfg = apply_overlay(merge(copy.deepcopy(before), frag))
    if dry:
        _diff_summary(before, cfg, f"install {name}", OVERLAY.exists())
        return True
    backup()
    save_json(CFG, cfg)

    state = load_json(STATE, {"installed": {}})
    state["installed"][name] = {"at": datetime.now().isoformat(), "fragment": frag}
    save_json(STATE, state)
    print(f"  [ok] {name} installed")
    return True


def _fragment_for(name: str, entry: dict | None) -> dict:
    """Fragment to unmerge for `name`: install-time snapshot if recorded,
    else live system.json (legacy state), else {}."""
    if entry and entry.get("fragment"):
        return entry["fragment"]
    return load_json(SYSTEMS / name / "system.json", {})


def remove(name: str, dry: bool = False) -> bool:
    state = load_json(STATE, {"installed": {}})
    entry = state["installed"].pop(name, None)
    frag = _fragment_for(name, entry)
    if not frag and entry is None:
        print(f"  [err] system '{name}' not found")
        return False
    overlay = load_json(OVERLAY, {})
    # 2. Unmerge the removed fragment.
    before = load_json(CFG, {})
    cfg = unmerge(copy.deepcopy(before), frag)
    # 3. Hard-clean agents: drop any agent the fragment defined unless a
    #    surviving installed system also defines it or the overlay owns it —
    #    plain unmerge leaves stubs when the live value diverged (e.g. the
    #    user or a residue key changed a leaf).
    survivors = {}
    for other, oentry in state["installed"].items():
        survivors[other] = _fragment_for(other, oentry)
    survivor_agents = {a for f in survivors.values() for a in (f.get("agents") or {})}
    overlay_agents = set((overlay.get("agents") or {}).keys())
    cfg_agents = cfg.get("agents") or {}
    for a in (frag.get("agents") or {}):
        if a in cfg_agents and a not in survivor_agents and a not in overlay_agents:
            del cfg_agents[a]
    # 4. Scalars owned by the fragment (default_agent/model): delete even if
    #    the live value diverged; survivors/overlay restore below if they
    #    define them — else they stay gone.
    for k in ("default_agent", "model"):
        if k in frag and k not in overlay:
            cfg.pop(k, None)
    # 5. Re-merge every remaining installed system — restores keys shared
    #    with the removed fragment that unmerge stripped (e.g. instructions).
    for f in survivors.values():
        cfg = merge(cfg, f)
    # 6. User overlay always last.
    cfg = merge(cfg, overlay)
    if dry:
        _diff_summary(before, cfg, f"remove {name}", bool(overlay))
        return True
    backup()
    # State was already popped above — the removed system can't re-apply itself.
    save_json(STATE, state)
    save_json(CFG, cfg)
    print(f"  [ok] {name} removed")
    return True


def split_agents(agents: dict) -> tuple[list, list]:
    d = {a: v for a, v in agents.items() if isinstance(v, dict)}
    prim = sorted(a for a, v in d.items() if (v.get("mode") or "primary") in ("primary", "all"))
    subs = sorted(a for a, v in d.items() if v.get("mode") == "subagent")
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
    drifts = 0
    def chk(name, good, extra=""):
        nonlocal ok
        ok &= good
        print(f"  [{'ok' if good else 'FAIL'}] {name} {extra}")
    def drift(name, extra="run: agentsys sync"):
        nonlocal drifts
        drifts += 1
        print(f"  [drift] {name} — {extra}")
    def info(name):
        print(f"  [warn] {name}")
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
    state = load_json(STATE, {"installed": {}})["installed"]
    overlay = load_json(OVERLAY, {})
    overlay_agents = overlay.get("agents") or {}
    overlay_instr = set(overlay.get("instructions") or [])
    cfg_agents = cfg.get("agents") or {}
    cfg_instr = set(cfg.get("instructions") or [])
    for name in system_dirs():
        frag = load_json(SYSTEMS / name / "system.json", {})
        frag_agents = frag.get("agents") or {}
        # a system counts as installed if tracked in state or all agents present
        installed = name in state or (frag_agents
                                    and all(a in cfg_agents for a in frag_agents))
        for a, spec in frag_agents.items():
            present = a in cfg_agents
            chk(f"agent {a} ({name})", present or not installed)
            if present and installed:
                # user-overridden agents are intentional, not drift
                if a in overlay_agents:
                    continue
                live = cfg_agents[a] if isinstance(cfg_agents[a], dict) else {}
                want = spec if isinstance(spec, dict) else {}
                if (live.get("system") or "") != (want.get("system") or ""):
                    drift(f"agent {a} ({name}) — system prompt differs")
        if installed:
            frag_instr = set(frag.get("instructions") or [])
            # frag instructions must all be present in the merged config;
            # items re-added by the overlay count as covered
            if frag_instr and not frag_instr.issubset(cfg_instr | overlay_instr):
                missing = sorted(frag_instr - cfg_instr - overlay_instr)
                drift(f"instructions ({name}) — missing: {', '.join(missing)}")
    # untracked agents: in cfg but not owned by any installed system nor the
    # overlay (residue from older remove/unmerge paths)
    tracked = set()
    for name in system_dirs():
        frag = load_json(SYSTEMS / name / "system.json", {})
        frag_agents = frag.get("agents") or {}
        installed = name in state or (frag_agents
                                    and all(a in cfg_agents for a in frag_agents))
        if installed:
            tracked |= set(frag_agents)
    for a in sorted(cfg_agents):
        if a not in tracked and a not in overlay_agents:
            info(f"agent {a} untracked — not defined by any installed system "
                 f"nor covered by overrides")
    remote = remote_tag()
    local = local_version()
    if remote and local and _ver(remote) > _ver(local):
        info(f"repo updated to {remote} but local is {local} — run: agentsys update")
    if not ok:
        print("doctor: issues found")
    elif drifts:
        print(f"doctor: healthy, {drifts} drift(s) — run: agentsys sync")
    else:
        print("doctor: healthy")


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
    state = load_json(STATE, {"installed": {}})
    names = set(state["installed"].keys())
    # also detect systems whose agents are present but not state-tracked
    for n in system_dirs():
        frag = load_json(SYSTEMS / n / "system.json", {})
        ags = (frag.get("agents") or {}).keys()
        if ags and all(a in cfg_agents for a in ags):
            names.add(n)
    overlay = load_json(OVERLAY, {})
    overlay_agents = set((overlay.get("agents") or {}).keys())
    for name in names:
        frag = _fragment_for(name, state["installed"].get(name))
        if frag:
            cfg = unmerge(cfg, frag)
            # hard-clean: drop agents owned by the removed system unless the
            # overlay covers them (overlay-owned keys persist by design)
            for a in (frag.get("agents") or {}):
                if a in (cfg.get("agents") or {}) and a not in overlay_agents:
                    del cfg["agents"][a]
        print(f"  [unmerged] {name}")
    # drop leftover cfg agents not owned by any system nor the overlay —
    # untracked residue that unmerge alone would leave behind
    system_agents = set()
    for n in system_dirs():
        system_agents |= set((load_json(SYSTEMS / n / "system.json", {})
                              .get("agents") or {}).keys())
    for a in list((cfg.get("agents") or {}).keys()):
        if a not in system_agents and a not in overlay_agents:
            del cfg["agents"][a]
            print(f"  [dropped] untracked agent {a}")
    # user overrides were merged last on install — unmerge them too so the
    # config is clean; the FILE stays on disk (user data).
    if overlay:
        cfg = unmerge(cfg, overlay)
        print(f"  [unmerged] user overrides")
    backup()
    save_json(CFG, cfg)
    if OVERLAY.exists():
        print(f"  note: user overrides kept at {OVERLAY}")
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
        dry = "--dry-run" in rest or "-n" in rest
        names = [n for n in rest if n not in ("--dry-run", "-n")]
        return 0 if all(install(n, dry) for n in names) else 1
    if cmd == "remove":
        dry = "--dry-run" in rest or "-n" in rest
        names = [n for n in rest if n not in ("--dry-run", "-n")]
        return 0 if all(remove(n, dry) for n in names) else 1
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
        ver = local_version() or "dev checkout"
        print(f"agentsys {ver} —" + USAGE.split("—", 1)[1])
        notice_update()   # post-hook: runs on EVERY command path
        return 0
    cmd, rest = args[0], args[1:]
    rc = _dispatch(cmd, rest)
    # notice_update() caches to STATE — a write; skip on dry-run
    if cmd != "update" and "--dry-run" not in rest and "-n" not in rest:
        notice_update()
    return rc


if __name__ == "__main__":
    sys.exit(main())
