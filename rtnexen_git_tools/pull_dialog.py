import wx
import threading

from .i18n import t, t_en
from .common import APPNAME, _run, get_dialog_size, center_on_screen, _build_target_choices
from .base_dialog import BaseGitDialog

# ── Pull Form Dialog ──────────────────────────────────────────────────────────

class PullDialog(BaseGitDialog):
    def __init__(self, project_path):
        super().__init__(t_en("subtitle_pull"), project_path,
                         size=get_dialog_size(0.42, 0.45))
        p  = self.panel
        cs = self.content_sizer

        choices, self.targets = _build_target_choices(project_path)

        cs.AddSpacer(14)
        self.target_radio = wx.RadioBox(p, label=t("target"),
                                         choices=choices,
                                         majorDimension=len(choices),
                                         style=wx.RA_SPECIFY_COLS)
        cs.Add(self.target_radio, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        cs.AddSpacer(10)
        warn = wx.StaticText(p, label=t("pull_warning"))
        cs.Add(warn, 0, wx.LEFT | wx.RIGHT | wx.TOP, 14)

        cs.AddStretchSpacer()
        self.add_bottom_buttons(t("btn_pull_submit"))
        self.FinalizeLayout()

    def GetTargets(self):
        sel = self.target_radio.GetStringSelection()
        if sel == "ALL":
            return list(self.targets)
        return [cfg for cfg in self.targets if cfg["name"] == sel] or [self.targets[0]]

# ── Pull conflict resolution ──────────────────────────────────────────────────

def _is_non_fast_forward(text):
    markers = (
        "non-fast-forward",
        "Updates were rejected",
        "fetch first",
        "behind its remote counterpart",
    )
    return any(m in text for m in markers)

def _is_merge_conflict(text):
    markers = (
        "CONFLICT",
        "Automatic merge failed",
        "fix conflicts and then commit",
    )
    return any(m in text for m in markers)

def _build_conflict_message(summary, files=None, extra=None):
    lines = [summary, ""]
    if files:
        lines.append(t("conflict_affected_files"))
        for f in files[:15]:
            lines.append(f"  {f}")
        if len(files) > 15:
            lines.append(t("conflict_more_files", n=len(files) - 15))
        lines.append("")
    if extra:
        lines.append(extra)
        lines.append("")
    lines.append(t("conflict_choose"))
    lines.append(t("conflict_keep_local_desc"))
    lines.append(t("conflict_overwrite_local_desc"))
    return "\n".join(lines)

def _ask_conflict_dialog(title, message):
    """Show Keep Local / Overwrite Local / Cancel from the UI thread and block
    the calling (worker) thread until the user responds."""
    result = {"choice": wx.ID_CANCEL}
    done = threading.Event()

    def _show():
        dlg = wx.MessageDialog(
            None, message, f"{APPNAME} — {title}",
            wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
        dlg.SetYesNoCancelLabels(t("btn_overwrite_local"), t("btn_keep_local"), t("cancel"))
        center_on_screen(dlg)
        result["choice"] = dlg.ShowModal()
        dlg.Destroy()
        done.set()

    wx.CallAfter(_show)
    done.wait()
    return result["choice"]

def _get_branch(path):
    """Return the current branch name, or empty string if detached/unknown."""
    r = _run(["git", "branch", "--show-current"], path)
    return r.stdout.strip() if r.returncode == 0 else ""

def _ensure_upstream(log, path, branch):
    """If current branch has no upstream, set it to origin/<branch>.
    Returns True if upstream is confirmed available (existing or just set)."""
    r = _run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], path)
    if r.returncode == 0:
        return True  # upstream already set
    if not branch:
        return False
    log(t("log_upstream_set", branch=branch))
    rs = _run(["git", "branch", "--set-upstream-to", f"origin/{branch}", branch], path)
    if rs.returncode != 0:
        log(t("log_upstream_fail"))
        return False
    return True

def _do_pull(log, path, branch):
    """Run pull with explicit remote/branch to avoid bare-pull failures."""
    if branch:
        return _run(["git", "pull", "origin", branch], path)
    return _run(["git", "pull"], path)

def _overwrite_local(log, path, branch):
    """Scenario A/C: discard local changes (abort merge if any) then re-pull."""
    merge_head = _run(["git", "rev-parse", "-q", "--verify", "MERGE_HEAD"], path)
    if merge_head.returncode == 0:
        log(t("log_merge_abort"))
        r = _run(["git", "merge", "--abort"], path)
        if r.returncode != 0 and r.stderr.strip():
            log(f"   {r.stderr.strip()}")

    log(t("log_discard_local"))
    r = _run(["git", "checkout", "--", "."], path)
    if r.returncode != 0:
        log(t("log_discard_failed", err=r.stderr.strip()))
        return False

    log(t("log_repulling"))
    r = _do_pull(log, path, branch)
    out = r.stdout.strip()
    err = r.stderr.strip()
    if r.returncode != 0:
        log(t("log_pull_failed", combined=(out + "\n" + err).strip()))
        return False

    if out:
        log(out)
    log(t("log_pull_overwritten"))
    if "Already up to date" not in out:
        log(t("log_reload_hint"))
    return True

def _reset_to_remote(log, path, branch):
    """Scenario B: force-sync local to remote via fetch + reset --hard."""
    log(t("log_reset_to_remote"))
    rf = _run(["git", "fetch", "origin"], path)
    if rf.returncode != 0:
        log(t("log_reset_failed", err=rf.stderr.strip()))
        return False
    ref = f"origin/{branch}" if branch else "origin"
    rr = _run(["git", "reset", "--hard", ref], path)
    if rr.returncode != 0:
        log(t("log_reset_failed", err=rr.stderr.strip()))
        return False
    log(t("log_reset_done"))
    log(t("log_reload_hint"))
    return True

def _pull_one(log, path):
    """Pull the repo at `path`. Returns True if the caller may continue to
    the next target (ALL mode), False if the user aborted or it failed."""
    branch = _get_branch(path)

    # ── Scenario A: uncommitted local changes ─────────────────────────────
    log(t("log_checking_status"))
    st = _run(["git", "status", "--porcelain"], path)
    if st.stdout.strip():
        changed = st.stdout.strip().splitlines()
        log(t("log_uncommitted"))
        for l in changed:
            log(f"   {l}")

        msg = _build_conflict_message(
            t("conflict_uncommitted_summary"),
            files=[l[3:] for l in changed])
        choice = _ask_conflict_dialog(t("conflict_uncommitted_title"), msg)
        if choice == wx.ID_YES:
            log("")
            _ensure_upstream(log, path, branch)
            return _overwrite_local(log, path, branch)
        else:
            log(t("log_pull_cancel_keep"))
            return False

    # ── Ensure upstream is set before pulling ────────────────────────────
    _ensure_upstream(log, path, branch)

    log(t("log_running_pull"))
    r = _do_pull(log, path, branch)
    out = r.stdout.strip()
    err = r.stderr.strip()
    combined = (out + "\n" + err).strip()

    if r.returncode != 0:
        # ── Scenario B: non-fast-forward ──────────────────────────────────
        if _is_non_fast_forward(combined):
            log(t("log_non_ff", combined=combined))
            msg = _build_conflict_message(t("conflict_nonff_summary"))
            choice = _ask_conflict_dialog(t("conflict_nonff_title"), msg)
            if choice == wx.ID_YES:
                log("")
                return _reset_to_remote(log, path, branch)
            else:
                log(t("log_pull_cancel_retry"))
                return False

        # ── Scenario C: post-pull merge conflict ──────────────────────────
        if _is_merge_conflict(combined):
            conflicted = _run(["git", "diff", "--name-only", "--diff-filter=U"], path)
            files = conflicted.stdout.strip().splitlines()
            log(t("log_merge_conflict", combined=combined))
            if files:
                log(t("log_conflict_files"))
                for f in files:
                    log(f"  {f}")
            msg = _build_conflict_message(t("conflict_merge_summary"), files=files)
            choice = _ask_conflict_dialog(t("conflict_merge_title"), msg)
            if choice == wx.ID_YES:
                log("")
                return _overwrite_local(log, path, branch)
            else:
                log(t("log_merge_conflict_cancel"))
                return False

        log(t("log_pull_failed", combined=combined))
        return False

    if out:
        log(out)
    log(t("log_pull_done"))
    if "Already up to date" not in out:
        log(t("log_reload_hint"))
    return True

def _pull_all_fn(log, project_path):
    targets = _pull_all_fn._targets
    for cfg in targets:
        if len(targets) > 1:
            log(f"\n══════ {cfg['name']} ══════")
        if not _pull_one(log, cfg["path"]):
            break
