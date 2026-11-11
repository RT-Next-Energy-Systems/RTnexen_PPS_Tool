import wx
import os
import threading
from datetime import datetime

from .i18n import t
from .common import (APPNAME, ID_BACK, _run, is_git_repo, get_dialog_size,
                      untrack_ignored_files, ask_push_nff_dialog,
                      _rebase_in_progress, ask_stuck_rebase_dialog,
                      porcelain_lines, pull_rebase_or_rollback, watch_open_board,
                      force_push_fresh_lease, is_repo_root)
from .base_dialog import BaseGitDialog
from .pull_dialog import (
    _get_branch, _ensure_upstream, _do_pull, _discard_local_changes, _take_remote,
    _reset_to_remote, _abort_merge_if_any,
    _is_non_fast_forward, _is_merge_conflict, _build_conflict_message,
)

from .push_dialog import _ensure_gitignore

# ── Folder scanning ────────────────────────────────────────────────────────

def scan_batch_repos(root_path):
    """Return a sorted list of {"name": folder_name, "path": full_path} for
    every immediate subfolder of root_path that is a git repository.
    Non-git subfolders are silently skipped."""
    repos = []
    if not root_path or not os.path.isdir(root_path):
        return repos
    for entry in sorted(os.listdir(root_path)):
        if entry.startswith("."):
            continue  # .git, .history, ... are never projects
        full = os.path.join(root_path, entry)
        if os.path.isdir(full) and is_repo_root(full):
            repos.append({"name": entry, "path": full})
    return repos

# ── Batch conflict dialog (adds "apply to all remaining") ──────────────────

def _ask_batch_conflict_dialog(title, message, allow_apply_all):
    """Like pull_dialog._ask_conflict_dialog, but offers an extra checkbox
    to apply the same choice to all remaining repos in this batch run.
    Returns (choice, apply_all) where choice is wx.ID_YES/ID_NO/ID_CANCEL."""
    result = {"choice": wx.ID_CANCEL, "apply_all": False}
    done = threading.Event()

    def _show():
        dlg = wx.MessageDialog(
            None, message + (t("batch_apply_all_hint") if allow_apply_all else ""),
            f"{APPNAME} — {title}",
            wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
        dlg.SetYesNoCancelLabels(t("btn_overwrite_local"), t("btn_keep_local"), t("cancel"))
        choice = dlg.ShowModal()
        dlg.Destroy()
        result["choice"] = choice
        if allow_apply_all and choice in (wx.ID_YES, wx.ID_NO):
            confirm = wx.MessageDialog(
                None, t("batch_apply_all_hint").strip(),
                f"{APPNAME} — {title}", wx.YES_NO | wx.ICON_QUESTION)
            confirm.SetYesNoLabels(t("ok"), t("cancel"))
            result["apply_all"] = confirm.ShowModal() == wx.ID_YES
            confirm.Destroy()
        done.set()

    wx.CallAfter(_show)
    done.wait()
    return result["choice"], result["apply_all"]

# ── Batch Pull ───────────────────────────────────────────────────────────────

def _batch_pull_one(log, path, forced):
    """Pull a single repo. `forced` maps a prompt kind ("uncommitted", "nonff",
    "conflict") to the answer the user chose "for all remaining repos".

    The kinds are kept apart on purpose: "overwrite all" chosen for UNCOMMITTED
    changes must never also answer a MERGE-CONFLICT prompt — that one resets
    to the remote and discards committed, unpushed work.
    Returns (outcome, forced) where outcome is "ok"/"skipped"/"failed"."""
    forced = dict(forced or {})
    branch = _get_branch(path)

    def ask(kind, title, msg):
        if kind in forced:
            return forced[kind]
        choice, apply_all = _ask_batch_conflict_dialog(title, msg, allow_apply_all=True)
        if apply_all and choice in (wx.ID_YES, wx.ID_NO):
            forced[kind] = choice
        return choice

    log(t("log_checking_status"))
    st = _run(["git", "status", "--porcelain"], path)
    changed = porcelain_lines(st.stdout)
    if changed:
        log(t("log_uncommitted"))
        for l in changed:
            log(f"   {l}")
        choice = ask("uncommitted", t("conflict_uncommitted_title"),
                     _build_conflict_message(t("conflict_uncommitted_summary"), files=[l[3:] for l in changed]))
        if choice != wx.ID_YES:
            log(t("log_pull_cancel_keep"))
            return "skipped", forced
        log("")
        if not _discard_local_changes(log, path):
            return "failed", forced
        # clean now — fall through to the normal pull

    _ensure_upstream(log, path, branch)

    log(t("log_running_pull"))
    r = _do_pull(log, path, branch)
    out = r.stdout.strip()
    err = r.stderr.strip()
    combined = (out + "\n" + err).strip()

    if r.returncode != 0:
        if _is_non_fast_forward(combined):
            log(t("log_non_ff", combined=combined))
            choice = ask("nonff", t("conflict_nonff_title"), _build_conflict_message(t("conflict_nonff_summary")))
            if choice == wx.ID_YES:
                log("")
                return ("ok" if _reset_to_remote(log, path, branch) else "failed"), forced
            log(t("log_pull_cancel_retry"))
            return "skipped", forced

        if _is_merge_conflict(combined):
            conflicted = _run(["git", "diff", "--name-only", "--diff-filter=U"], path)
            files = conflicted.stdout.strip().splitlines()
            log(t("log_merge_conflict", combined=combined))
            if files:
                log(t("log_conflict_files"))
                for f in files:
                    log(f"  {f}")
            choice = ask("conflict", t("conflict_merge_title"),
                         _build_conflict_message(t("conflict_merge_summary"), files=files))
            if choice == wx.ID_YES:
                log("")
                return ("ok" if _take_remote(log, path, branch) else "failed"), forced
            _abort_merge_if_any(log, path)
            log(t("log_merge_conflict_cancel"))
            return "skipped", forced

        log(t("log_pull_failed", combined=combined))
        return "failed", forced

    if out:
        log(out)
    log(t("log_pull_done"))
    return "ok", forced

def _batch_pull_fn(log, root_path):
    repos = scan_batch_repos(root_path)
    forced = {}   # prompt kind -> answer the user chose "for all remaining repos"
    results = []
    for cfg in repos:
        log(f"\n══════ {cfg['name']} ══════")
        outcome, forced = _batch_pull_one(log, cfg["path"], forced)
        results.append((cfg["name"], outcome))

    log(f"\n\n══════ {t('batch_summary_title')} ══════")
    for name, outcome in results:
        icon = {"ok": "✓", "skipped": "⏭", "failed": "✗"}.get(outcome, "?")
        log(f"  {icon}  {name} — {outcome}")

# ── Batch Push ───────────────────────────────────────────────────────────────

def _batch_push_one(log, path, commit_msg):
    _ensure_gitignore(log, path)

    removed = untrack_ignored_files(path)
    tracked_history = _run(["git", "ls-files", "--cached", "--", ".history"], path)
    if tracked_history.stdout.strip():
        _run(["git", "rm", "-r", "--cached", "--", ".history"], path)
        if ".history" not in removed:
            removed.append(".history")
    if removed:
        log(t("log_untracked_history"))

    branch_now = _run(["git", "branch", "--show-current"], path).stdout.strip()
    _ensure_upstream(log, path, branch_now)

    st = _run(["git", "status", "--porcelain"], path)
    has_changes = bool(st.stdout.strip())

    unpushed = _run(["git", "log", "@{u}..HEAD", "--oneline"], path)
    has_unpushed = bool(unpushed.stdout.strip()) if unpushed.returncode == 0 else True

    if not has_changes and not has_unpushed:
        log(t("batch_skip_clean"))
        return "skipped"

    if has_changes:
        log(t("log_staging"))
        r = _run(["git", "add", "-A"], path)
        if r.stdout.strip(): log(r.stdout.strip())

        log(t("log_committing", msg=commit_msg))
        r = _run(["git", "commit", "-F", "-"], path, input=commit_msg)
        if r.stdout.strip(): log(r.stdout.strip())
        if r.returncode != 0:
            err = r.stderr.strip() or r.stdout.strip()
            if "nothing to commit" not in err:
                log(t("log_commit_failed", err=err))
                return "failed"

    log(t("log_pushing"))
    args = ["git", "push", "origin", branch_now] if branch_now else ["git", "push", "origin"]
    r = _run(args, path)
    if r.stdout.strip(): log(r.stdout.strip())
    if r.returncode != 0:
        combined = (r.stdout.strip() + "\n" + r.stderr.strip()).strip()
        if _is_non_fast_forward(combined):
            log(t("log_push_non_ff"))
            choice = ask_push_nff_dialog()
            if choice == "pull_push":
                if _rebase_in_progress(path):
                    log(t("log_stuck_rebase_detected"))
                    if not ask_stuck_rebase_dialog():
                        log(t("log_push_skip_nff"))
                        return "skipped"
                    log(t("log_rebase_aborting_stale"))
                    r_abort = _run(["git", "rebase", "--abort"], path)
                    if r_abort.returncode != 0:
                        log(t("log_rebase_abort_failed", err=(r_abort.stderr.strip() or r_abort.stdout.strip())))
                        return "failed"
                log(t("log_rebase_before_push"))
                if not pull_rebase_or_rollback(log, path, branch_now):
                    return "failed"
                r2 = _run(args, path)
                if r2.stdout.strip(): log(r2.stdout.strip())
                if r2.returncode != 0:
                    log(t("log_push_failed", err=r2.stderr.strip()))
                    return "failed"
                log(t("log_push_done"))
                return "ok"
            elif choice == "force":
                return "ok" if force_push_fresh_lease(log, path, branch_now) else "failed"
            else:
                log(t("log_push_skip_nff"))
                return "skipped"
        log(t("log_push_failed", err=r.stderr.strip()))
        return "failed"
    log(t("log_push_done"))
    return "ok"

def _batch_push_fn(log, root_path):
    repos = scan_batch_repos(root_path)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = t("batch_auto_commit_msg", ts=ts)
    results = []
    for cfg in repos:
        log(f"\n══════ {cfg['name']} ══════")
        outcome = _batch_push_one(log, cfg["path"], commit_msg)
        results.append((cfg["name"], outcome))

    log(f"\n\n══════ {t('batch_summary_title')} ══════")
    for name, outcome in results:
        icon = {"ok": "✓", "skipped": "⏭", "failed": "✗"}.get(outcome, "?")
        log(f"  {icon}  {name} — {outcome}")

# ── Entry points ─────────────────────────────────────────────────────────────

def run_batch_push(root_path):
    from .operation_dialog import OperationDialog
    op = OperationDialog(t("subtitle_batch_push"), root_path, _batch_push_fn)
    watch_open_board(op.ShowModal)
    op.Destroy()

def run_batch_pull(root_path):
    from .operation_dialog import OperationDialog
    op = OperationDialog(t("subtitle_batch_pull"), root_path, _batch_pull_fn)
    watch_open_board(op.ShowModal)
    op.Destroy()
