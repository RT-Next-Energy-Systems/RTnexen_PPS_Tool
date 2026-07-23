import wx
import os
import subprocess
import platform

from .i18n import t, get_global_remote2

VERSION = "3.4.0"
APPNAME = "RTnexen PPS Tool"

ID_BACK = wx.ID_HIGHEST + 100

# ── subprocess wrapper (no terminal flash on Windows) ─────────────────────────

def _run(args, cwd):
    """Run a git command silently — no console window on Windows."""
    kwargs = dict(
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if platform.system() == "Windows":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    return subprocess.run(args, **kwargs)

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_git_repo(path):
    if not path or not os.path.isdir(path):
        return False
    r = _run(["git", "rev-parse", "--is-inside-work-tree"], path)
    return r.returncode == 0

def get_remote2_scope(project_path):
    """Return 'global' or 'project' — where Remote 2's name/path are
    persisted. Defaults to 'global' unless explicitly set to 'project'.
    The two scopes store independent data; switching the scope does not
    erase the other scope's saved values."""
    scope = _run(["git", "config", "--get", "rtnexen.remote2scope"], project_path).stdout.strip()
    return "project" if scope == "project" else "global"

def get_remote2_config(project_path):
    """Return (name2, path2) for Remote 2, read from whichever scope is
    currently selected for this project."""
    if get_remote2_scope(project_path) == "global":
        return get_global_remote2()
    name2 = _run(["git", "config", "--get", "rtnexen.remote2name"], project_path).stdout.strip()
    path2 = _run(["git", "config", "--get", "rtnexen.remote2path"], project_path).stdout.strip()
    return name2, path2

def get_target_configs(project_path):
    """Return a list of 1-2 independent targets this plugin can operate on:
    [{"name": str, "path": str, "kind": "project"|"library"}, ...]

    Slot 1 is always the currently open KiCad project (path=project_path).
    Slot 2 (optional) is a separate, independent local git repository (e.g. a
    self-built component library), configured in Settings — either stored
    per-project or globally for this device. The two are completely
    independent — neither is "primary"."""
    name1 = _run(["git", "config", "--get", "rtnexen.remote1name"], project_path).stdout.strip()
    configs = [{"name": name1 or t("default_remote1_name"), "path": project_path, "kind": "project"}]

    name2, path2 = get_remote2_config(project_path)
    if name2 and path2 and is_git_repo(path2):
        configs.append({"name": name2, "path": path2, "kind": "library"})

    return configs

def get_dialog_size(w_ratio=0.45, h_ratio=0.60):
    disp = wx.Display(0)
    geo  = disp.GetClientArea()
    return (max(int(geo.width * w_ratio), 800), max(int(geo.height * h_ratio), 650))

def center_on_screen(dlg):
    disp = wx.Display(0)
    geo  = disp.GetClientArea()
    w, h = dlg.GetSize()
    dlg.SetPosition(wx.Point(
        geo.x + (geo.width  - w) // 2,
        geo.y + (geo.height - h) // 2,
    ))

def untrack_ignored_files(path):
    """Remove tracked files that now match .gitignore from the git index.
    Returns list of paths that were untacked (empty list if none)."""
    r = _run(["git", "ls-files", "--cached", "--ignored", "--exclude-standard"], path)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    files = r.stdout.strip().splitlines()
    for f in files:
        _run(["git", "rm", "-r", "--cached", "--", f], path)
    return files

# ── Target selector helper ──────────────────────────────────────────────────

def _build_target_choices(project_path):
    """Return (choices, configs) for the ALL / XXX / YYY radio selector.
    `configs` is the list returned by get_target_configs()."""
    configs = get_target_configs(project_path)
    if len(configs) >= 2:
        choices = ["ALL"] + [c["name"] for c in configs]
    else:
        choices = [c["name"] for c in configs]
    return choices, configs
