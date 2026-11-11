import wx
import os
import subprocess
import platform
import threading

from .i18n import t, get_global_remote2

VERSION = "3.5.3"
APPNAME = "RTnexen PPS Tool"

ID_BACK = wx.ID_HIGHEST + 100

# ── subprocess wrapper (no terminal flash on Windows) ─────────────────────────

def _run(args, cwd, input=None):
    """Run a git command silently — no console window on Windows.

    - Output is always decoded as UTF-8 (what git emits). Relying on the
      locale default breaks on e.g. Traditional-Chinese Windows (cp950):
      a Chinese commit message or file name raised UnicodeDecodeError and
      killed the worker thread.
    - core.quotepath=false so non-ASCII paths come out readable instead of
      as "\\346\\226..." octal escapes.
    - git's own messages are forced to English (see below).
    - `input` (str) is sent on stdin as UTF-8 — used for commit messages so
      their bytes are UTF-8 whatever the OS / locale code page (argv is
      encoded with the locale's code page on Linux/macOS).
    - A missing git executable (or a vanished cwd) returns a failed result
      instead of raising, so callers' normal error handling applies."""
    args = list(args)
    env = None
    if args and args[0] == "git":
        args = ["git", "-c", "core.quotepath=false"] + args[1:]
        # Force untranslated (English) git messages: the plugin detects
        # situations by matching git's text ("CONFLICT", "nothing to commit",
        # "non-fast-forward", ...). With a localized git (e.g. zh_TW) none of
        # those matched — a merge conflict was reported as a generic failure
        # and "nothing to commit" aborted the push as "Commit failed".
        env = dict(os.environ)
        env.pop("LANGUAGE", None)
        env["LC_ALL"] = "C"
    kwargs = dict(
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL if input is None else None,
        input=input,
    )
    if platform.system() == "Windows":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        return subprocess.run(args, **kwargs)
    except OSError as e:
        return subprocess.CompletedProcess(args, 127, "", str(e))

def porcelain_lines(stdout):
    """Split `git status --porcelain` output into lines WITHOUT stripping the
    leading space of the status column (" M file"). Calling .strip() on the
    whole output used to eat that space on the first line, so l[3:] then cut
    the first character off the file name."""
    return [l for l in stdout.splitlines() if l.strip()]

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_git_repo(path):
    if not path or not os.path.isdir(path):
        return False
    r = _run(["git", "rev-parse", "--is-inside-work-tree"], path)
    return r.returncode == 0

def is_repo_root(path):
    """True only if `path` is the top level of its own repository. A plain
    sub-folder of a repo also passes `is_git_repo` (it is "inside a work
    tree"); treating it as a separate repo makes "its" push commit the whole
    enclosing repository."""
    if not is_git_repo(path):
        return False
    r = _run(["git", "rev-parse", "--show-toplevel"], path)
    if r.returncode != 0 or not r.stdout.strip():
        return False
    return _same_path(r.stdout.strip(), path)

def _same_path(a, b):
    norm = lambda p: os.path.normcase(os.path.realpath(p))
    return norm(a) == norm(b)

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
    if name2 and path2 and is_repo_root(path2):
        top = _run(["git", "rev-parse", "--show-toplevel"], project_path).stdout.strip()
        if not (top and _same_path(top, path2)):      # not the project's own repo again
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

def _rebase_in_progress(path):
    """True if the repo at `path` has a leftover `.git/rebase-merge` or
    `.git/rebase-apply` directory — i.e. a rebase (almost always this
    plugin's own "Pull & Push" sync step, run via `git pull --rebase`) was
    started but never finished (interrupted by a conflict, a crash, or the
    dialog being closed mid-operation).

    Git refuses to start a new rebase while one is already in progress. If
    this isn't caught first, the next "Pull & Push" attempt fails immediately
    with git's raw, unrecoverable-looking error ("It seems that there is
    already a rebase-merge directory ..."), and the user has no way to
    recover short of running git commands by hand outside the plugin."""
    r = _run(["git", "rev-parse", "--git-dir"], path)
    git_dir = r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else ".git"
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(path, git_dir)
    return os.path.isdir(os.path.join(git_dir, "rebase-merge")) or \
           os.path.isdir(os.path.join(git_dir, "rebase-apply"))

def ask_stuck_rebase_dialog():
    """Show a dialog from the UI thread when a leftover, unfinished rebase is
    blocking the pull-before-push sync step. Returns True if the user wants
    to abort the stale rebase and retry, False to skip this target instead."""
    result = {"choice": False}
    done = threading.Event()

    def _show():
        dlg = wx.MessageDialog(
            None,
            t("stuck_rebase_msg"),
            f"{APPNAME} — {t('stuck_rebase_title')}",
            wx.YES_NO | wx.ICON_WARNING)
        dlg.SetYesNoLabels(t("btn_abort_rebase_retry"), t("cancel"))
        r = dlg.ShowModal()
        dlg.Destroy()
        result["choice"] = (r == wx.ID_YES)
        done.set()

    wx.CallAfter(_show)
    done.wait()
    return result["choice"]

def untrack_ignored_files(path):
    """Remove tracked files that now match .gitignore from the git index.
    Returns list of paths that were untacked (empty list if none)."""
    # -z: NUL-separated, never quoted — otherwise non-ASCII names come back
    # quoted/escaped and the `git rm` below silently fails to match them.
    r = _run(["git", "ls-files", "-z", "--cached", "--ignored", "--exclude-standard"], path)
    if r.returncode != 0 or not r.stdout.strip("\0"):
        return []
    files = [f for f in r.stdout.split("\0") if f]
    for f in files:
        _run(["git", "rm", "-r", "--cached", "--", f], path)
    return files

def pull_rebase_or_rollback(log, path, branch):
    """`git pull --rebase` for the Pull & Push recovery. If it fails (usually
    a conflict), abort the rebase right away instead of leaving the repo
    mid-rebase: a detached HEAD with <<<<<<< markers inside .kicad_sch /
    .kicad_pcb files that KiCad can no longer open. Returns True on success."""
    args = ["git", "pull", "--rebase", "origin", branch] if branch else ["git", "pull", "--rebase"]
    r = _run(args, path)
    if r.returncode == 0:
        return True
    log(t("log_rebase_before_push_fail", err=(r.stderr.strip() or r.stdout.strip())))
    if _rebase_in_progress(path):
        ra = _run(["git", "rebase", "--abort"], path)
        if ra.returncode == 0:
            log(t("log_rebase_rolled_back"))
        else:
            log(t("log_rebase_abort_failed", err=(ra.stderr.strip() or ra.stdout.strip())))
    return False

def force_push_fresh_lease(log, path, branch):
    """Overwrite origin/<branch> with the local branch.

    Fetch first: a rejected `git push` does NOT update the remote-tracking
    ref, so a bare `--force-with-lease` compared against stale info and was
    rejected every time ("! [rejected] ... (stale info)") — the "Force Push"
    button never worked when a teammate had pushed. After the fetch the lease
    is the remote state we just looked at (and listed to the user), so a push
    landing in between is still refused. Returns True on success."""
    if not branch:
        log(t("log_overwrite_no_branch"))
        return False
    log(t("log_overwrite_fetching"))
    r_fetch = _run(["git", "fetch", "origin", branch], path)
    if r_fetch.returncode != 0:
        err = r_fetch.stderr.strip() or r_fetch.stdout.strip()
        # A branch that doesn't exist on the remote yet is fine — nothing to overwrite.
        if "couldn't find remote ref" not in err.lower():
            log(t("log_overwrite_fetch_fail", err=err))
            return False
    else:
        dropped = _run(["git", "log", "--oneline", f"HEAD..refs/remotes/origin/{branch}"], path)
        if dropped.returncode == 0 and dropped.stdout.strip():
            log(t("log_overwrite_will_drop", commits=dropped.stdout.strip()))
    log(t("log_force_pushing"))
    r_f = _run(["git", "push", "--force-with-lease", "origin", branch], path)
    if r_f.stdout.strip(): log(r_f.stdout.strip())
    if r_f.returncode != 0:
        log(t("log_force_push_failed", err=r_f.stderr.strip()))
        return False
    log(t("log_force_push_done"))
    return True

# ── Open-board staleness tracking (Pull → Push in the same KiCad session) ────
# run_push() saves the board currently open in pcbnew before committing. If a
# Pull just rewrote that .kicad_pcb on disk, the editor still holds the OLD
# board in memory, and saving it would silently revert the pulled changes
# (and then commit + push the revert). We remember the file's signature right
# after a pull changed it; while the file is still exactly that version, the
# in-memory board is treated as stale and is not saved over it.

_PULLED_BOARDS = {}

def _file_sig(p):
    try:
        st = os.stat(p)
        return (st.st_mtime_ns, st.st_size)
    except (OSError, TypeError, ValueError):
        return None

def open_board_path():
    try:
        import pcbnew
        return pcbnew.GetBoard().GetFileName() or ""
    except Exception:
        return ""

def watch_open_board(fn):
    """Run fn() (a pull); afterwards, if the open board file changed on disk,
    mark it as stale in the editor."""
    path = open_board_path()
    before = _file_sig(path) if path else None
    try:
        return fn()
    finally:
        if path:
            after = _file_sig(path)
            if after is not None and after != before:
                _PULLED_BOARDS[path] = after

def save_open_board():
    """Save the board open in pcbnew. Returns "saved", "stale" (skipped: a
    pull updated the file and the editor hasn't saved since — saving now
    would overwrite the pulled version), or "none" (no board / save failed)."""
    path = open_board_path()
    if not path:
        return "none"
    marked = _PULLED_BOARDS.get(path)
    if marked is not None:
        if marked == _file_sig(path):
            return "stale"
        del _PULLED_BOARDS[path]  # saved from KiCad since the pull — fine again
    try:
        import pcbnew
        pcbnew.SaveBoard(path, pcbnew.GetBoard())
        return "saved"
    except Exception:
        return "none"

# ── Push non-fast-forward dialog (shared by push_dialog & batch_dialog) ──────

ID_FORCE_PUSH = wx.ID_HIGHEST + 101

def ask_push_nff_dialog():
    """Show Pull & Push / Force Push / Skip dialog from the UI thread.
    Returns 'pull_push', 'force', or 'skip'."""
    result = {"choice": "skip"}
    done = threading.Event()

    def _show():
        dlg = wx.MessageDialog(
            None,
            t("push_nff_msg"),
            f"{APPNAME} — {t('push_nff_title')}",
            wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
        dlg.SetYesNoCancelLabels(
            t("btn_pull_then_push"),
            t("btn_force_push"),
            t("btn_skip_push"))
        r = dlg.ShowModal()
        dlg.Destroy()
        if r == wx.ID_YES:
            result["choice"] = "pull_push"
        elif r == wx.ID_NO:
            result["choice"] = "force"
        else:
            result["choice"] = "skip"
        done.set()

    wx.CallAfter(_show)
    done.wait()
    return result["choice"]

# ── Target selector helper ──────────────────────────────────────────────────

def targets_for_choice(configs, index):
    """Targets for the radio button at `index` of the list built by
    _build_target_choices: [ALL, cfg0, cfg1] with two targets, [cfg0] with one.
    Matching by label text broke when Remote 2 was named "ALL" or shared a name."""
    if len(configs) >= 2:
        if index <= 0:
            return list(configs)
        return [configs[min(index - 1, len(configs) - 1)]]
    return [configs[0]]

def _build_target_choices(project_path):
    """Return (choices, configs) for the ALL / XXX / YYY radio selector.
    `configs` is the list returned by get_target_configs()."""
    configs = get_target_configs(project_path)
    if len(configs) >= 2:
        choices = ["ALL"] + [c["name"] for c in configs]
    else:
        choices = [c["name"] for c in configs]
    return choices, configs
