import wx
import os
import subprocess
import threading
import platform

VERSION = "2.3.0"
APPNAME = "RTnexen PPS Tool"

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
    r = _run(["git", "rev-parse", "--is-inside-work-tree"], path)
    return r.returncode == 0

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

# ── Base Dialog ───────────────────────────────────────────────────────────────

class BaseGitDialog(wx.Dialog):
    CYAN  = wx.Colour(0, 119, 252)
    GREEN = wx.Colour(76, 175, 80)
    DIM   = wx.Colour(160, 160, 160)
    HDR   = wx.Colour(28, 28, 36)

    def __init__(self, subtitle, project_path, size=None):
        if size is None:
            size = get_dialog_size()
        super().__init__(None, title=APPNAME,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                         size=size)
        self.project_path = project_path
        self.panel = wx.Panel(self)
        self.root_sizer = wx.BoxSizer(wx.VERTICAL)

        # ── Header ──
        hdr = wx.Panel(self.panel)
        hdr.SetBackgroundColour(self.HDR)
        hs = wx.BoxSizer(wx.HORIZONTAL)

        lbl = wx.StaticText(hdr, label=f"{APPNAME}  —  {subtitle}")
        lbl.SetForegroundColour(self.CYAN)
        lbl.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        hs.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 14)
        hs.AddStretchSpacer()

        self.branch_lbl = wx.StaticText(hdr, label="⎇  ...")
        self.branch_lbl.SetForegroundColour(self.GREEN)
        self.branch_lbl.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        hs.Add(self.branch_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        vlbl = wx.StaticText(hdr, label=f"v{VERSION}")
        vlbl.SetForegroundColour(self.DIM)
        hs.Add(vlbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        sbtn = wx.Button(hdr, label="⚙", size=(32, 32))
        sbtn.SetToolTip("Settings")
        sbtn.Bind(wx.EVT_BUTTON, self._on_settings)
        hs.Add(sbtn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        hdr.SetSizer(hs)
        hdr.SetMinSize((-1, 44))
        self.root_sizer.Add(hdr, 0, wx.EXPAND)

        self.content_sizer = wx.BoxSizer(wx.VERTICAL)
        self.root_sizer.Add(self.content_sizer, 1, wx.EXPAND)

        self.panel.SetSizer(self.root_sizer)
        self.SetMinSize((800, 650))
        wx.CallAfter(self._load_branch_async)

    def _load_branch_async(self):
        path = self.project_path
        def worker():
            r = _run(["git", "branch", "--show-current"], path)
            branch = r.stdout.strip() or "unknown"
            wx.CallAfter(self._set_branch, branch)
        threading.Thread(target=worker, daemon=True).start()

    def _set_branch(self, branch):
        if self.branch_lbl:
            self.branch_lbl.SetLabel(f"⎇  {branch}")

    def _on_settings(self, event):
        dlg = SettingsDialog(self.project_path)
        dlg.ShowModal()
        dlg.Destroy()

    def FinalizeLayout(self):
        self.panel.Layout()
        self.Layout()
        self.Fit()
        cur_w, cur_h = self.GetSize()
        min_w, min_h = self.GetMinSize()
        self.SetSize((max(cur_w, min_w), max(cur_h, min_h)))
        center_on_screen(self)

    def add_bottom_buttons(self, ok_label="OK", show_cancel=True):
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        ok = wx.Button(self.panel, wx.ID_OK, ok_label, size=(120, 36))
        ok.SetDefault()
        row.Add(ok, 0, wx.RIGHT, 10)
        if show_cancel:
            row.Add(wx.Button(self.panel, wx.ID_CANCEL, "Cancel", size=(90, 36)), 0)
        self.content_sizer.Add(row, 0, wx.EXPAND | wx.ALL, 12)
        return ok

# ── Settings Dialog ───────────────────────────────────────────────────────────

class SettingsDialog(wx.Dialog):
    def __init__(self, project_path):
        super().__init__(None, title=f"{APPNAME} — Settings",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                         size=get_dialog_size(0.38, 0.42))
        self.project_path = project_path
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        box = wx.StaticBox(panel, label=" GitHub Remote ")
        bs = wx.StaticBoxSizer(box, wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, hgap=12, vgap=10)
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(panel, label="Remote URL:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.url_ctrl = wx.TextCtrl(panel, value="loading...")
        grid.Add(self.url_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Branch:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.branch_lbl = wx.StaticText(panel, label="loading...")
        grid.Add(self.branch_lbl, 0, wx.ALIGN_CENTER_VERTICAL)

        bs.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        ab = wx.Button(panel, label="Apply Remote URL")
        ab.Bind(wx.EVT_BUTTON, self._apply)
        bs.Add(ab, 0, wx.LEFT | wx.BOTTOM, 10)
        sizer.Add(bs, 0, wx.EXPAND | wx.ALL, 12)

        info = wx.StaticBox(panel, label=" About ")
        info_s = wx.StaticBoxSizer(info, wx.VERTICAL)
        info_s.Add(wx.StaticText(panel, label=f"{APPNAME}  v{VERSION}"), 0, wx.ALL, 8)
        info_s.Add(wx.StaticText(panel, label="rtnexen@gmail.com"),
                   0, wx.LEFT | wx.BOTTOM, 8)
        sizer.Add(info_s, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        row.Add(wx.Button(panel, wx.ID_OK, "Close", size=(90, 32)), 0)
        sizer.Add(row, 0, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 12)

        panel.SetSizer(sizer)
        panel.Layout()
        self.Layout()
        center_on_screen(self)
        wx.CallAfter(self._load_async)

    def _load_async(self):
        path = self.project_path
        def worker():
            url    = _run(["git", "remote", "get-url", "origin"], path)
            branch = _run(["git", "branch", "--show-current"], path)
            wx.CallAfter(self.url_ctrl.SetValue,
                url.stdout.strip() if url.returncode == 0 else "(no remote set)")
            wx.CallAfter(self.branch_lbl.SetLabel,
                branch.stdout.strip() or "unknown")
        threading.Thread(target=worker, daemon=True).start()

    def _apply(self, event):
        url = self.url_ctrl.GetValue().strip()
        if not url:
            wx.MessageBox("URL cannot be empty.", "Error", wx.OK | wx.ICON_ERROR)
            return
        r = _run(["git", "remote", "set-url", "origin", url], self.project_path)
        if r.returncode == 0:
            wx.MessageBox(f"Remote URL updated:\n{url}", "Done", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(f"Failed:\n{r.stderr}", "Error", wx.OK | wx.ICON_ERROR)

# ── Main Menu Dialog ──────────────────────────────────────────────────────────

class MainMenuDialog(BaseGitDialog):
    def __init__(self, project_path):
        super().__init__("Select Action", project_path,
                         size=get_dialog_size(0.42, 0.62))
        p  = self.panel
        cs = self.content_sizer

        cs.AddSpacer(10)
        cs.Add(wx.StaticText(p, label="Choose an action:"), 0, wx.LEFT, 16)
        cs.AddSpacer(10)

        for label, tip, handler, color in [
            ("↑   Git Push",   "Commit & push changes to remote",  self._push,   wx.Colour(0, 119, 252)),
            ("↓   Git Pull",   "Pull latest changes from remote",   self._pull,   wx.Colour(255, 117, 31)),
            ("●   Git Status", "View branch, changes & recent log", self._status, wx.Colour(245, 219, 112)),
        ]:
            btn = wx.Button(p, label=label, size=(-1, 80))
            btn.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT,
                                wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            btn.SetForegroundColour(color)
            btn.SetToolTip(tip)
            btn.Bind(wx.EVT_BUTTON, handler)
            cs.Add(btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        cs.AddStretchSpacer()
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        row.Add(wx.Button(p, wx.ID_CANCEL, "Cancel", size=(90, 36)), 0)
        cs.Add(row, 0, wx.EXPAND | wx.ALL, 14)
        self.FinalizeLayout()

    def _push(self, e):
        self.EndModal(wx.ID_OK)
        run_push(self.project_path)

    def _pull(self, e):
        self.EndModal(wx.ID_OK)
        run_pull(self.project_path)

    def _status(self, e):
        self.EndModal(wx.ID_OK)
        run_status(self.project_path)

# ── Push Form Dialog ──────────────────────────────────────────────────────────

class PushDialog(BaseGitDialog):
    def __init__(self, project_path):
        super().__init__("Git Push", project_path,
                         size=get_dialog_size(0.45, 0.68))
        p  = self.panel
        cs = self.content_sizer

        cs.Add(wx.StaticText(p, label="Changed files:"), 0, wx.LEFT | wx.TOP, 14)
        self.status_text = wx.TextCtrl(p,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL, size=(-1, 110))
        self.status_text.SetFont(
            wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.status_text.SetValue("Loading...")
        cs.Add(self.status_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        cs.Add(wx.StaticText(p, label="Commit message:"), 0, wx.LEFT | wx.TOP, 14)
        self.msg_ctrl = wx.TextCtrl(p, style=wx.TE_MULTILINE, size=(-1, 70))
        self.msg_ctrl.SetFont(
            wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        cs.Add(self.msg_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        qrow = wx.BoxSizer(wx.HORIZONTAL)
        for lbl in ["Update schematic", "Update PCB layout", "Add component", "Fix DRC errors"]:
            b = wx.Button(p, label=lbl, size=(-1, 30))
            b.Bind(wx.EVT_BUTTON, lambda e, m=lbl: self.msg_ctrl.SetValue(m))
            qrow.Add(b, 1, wx.RIGHT, 4)
        cs.Add(qrow, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        self.add_bottom_buttons("Push ↑")
        self.FinalizeLayout()
        wx.CallAfter(self._load_async)

    def _load_async(self):
        path = self.project_path
        def worker():
            st     = _run(["git", "status", "--porcelain"], path)
            branch = _run(["git", "branch", "--show-current"], path)
            s = st.stdout.strip() or "(No changes — will push existing commits)"
            b = branch.stdout.strip()
            wx.CallAfter(self.status_text.SetValue, s)
            if b and b not in ("main", "master", "develop"):
                wx.CallAfter(self.msg_ctrl.SetValue, f"Update {b}")
        threading.Thread(target=worker, daemon=True).start()

    def GetMessage(self):
        return self.msg_ctrl.GetValue()

# ── Operation Dialog (live log output) ───────────────────────────────────────

class OperationDialog(BaseGitDialog):
    def __init__(self, subtitle, project_path, run_fn):
        super().__init__(subtitle, project_path,
                         size=get_dialog_size(0.45, 0.60))
        self.run_fn = run_fn
        p  = self.panel
        cs = self.content_sizer

        self.log = wx.TextCtrl(p,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL | wx.TE_RICH2)
        self.log.SetFont(
            wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.log.SetBackgroundColour(wx.Colour(20, 20, 28))
        self.log.SetForegroundColour(wx.Colour(220, 220, 220))
        cs.Add(self.log, 1, wx.EXPAND | wx.ALL, 12)

        self.gauge = wx.Gauge(p, range=100, size=(-1, 8))
        cs.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        self.close_btn = wx.Button(p, wx.ID_OK, "Close", size=(120, 36))
        self.close_btn.Disable()
        row.Add(self.close_btn, 0)
        cs.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.FinalizeLayout()
        wx.CallAfter(self._start)

    def _start(self):
        self.gauge.Pulse()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        def log(msg):
            wx.CallAfter(self._append, msg)
        self.run_fn(log, self.project_path)
        wx.CallAfter(self._finish)

    def _append(self, msg):
        if self.log:
            self.log.AppendText(msg + "\n")

    def _finish(self):
        if self.gauge:
            self.gauge.SetValue(100)
        if self.close_btn:
            self.close_btn.Enable()
            self.close_btn.SetDefault()
            self.close_btn.SetFocus()

# ── Git operation functions (run in background thread) ────────────────────────

def _push_fn(log, project_path):
    log("▶ Staging all changes...")
    r = _run(["git", "add", "-A"], project_path)
    if r.stdout.strip(): log(r.stdout.strip())

    commit_msg = _push_fn._commit_msg
    log(f"▶ Committing: \"{commit_msg}\"")
    r = _run(["git", "commit", "-m", commit_msg], project_path)
    if r.stdout.strip(): log(r.stdout.strip())
    if r.returncode != 0:
        err = r.stderr.strip() or r.stdout.strip()
        if "nothing to commit" in err:
            log("  (Nothing new to commit — pushing anyway)")
        else:
            log(f"\n✗  Commit failed: {err}")
            return

    log("▶ Pushing to remote...")
    r = _run(["git", "push"], project_path)
    if r.stdout.strip(): log(r.stdout.strip())
    if r.returncode != 0:
        log(f"\n✗  Push failed: {r.stderr.strip()}")
        return
    log("\n✓  Push complete!")

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
        lines.append("受影響的檔案 (Affected files):")
        for f in files[:15]:
            lines.append(f"  {f}")
        if len(files) > 15:
            lines.append(f"  ... 以及其他 {len(files) - 15} 個檔案")
        lines.append("")
    if extra:
        lines.append(extra)
        lines.append("")
    lines.append("請選擇處理方式：")
    lines.append("• 保留本地 (Keep Local)：取消 Pull，不做任何變更，請自行處理")
    lines.append("• 覆蓋本地 (Overwrite Local)：捨棄本地變更並以遠端版本覆蓋")
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
        dlg.SetYesNoCancelLabels("覆蓋本地 (Overwrite Local)", "保留本地 (Keep Local)", "Cancel")
        center_on_screen(dlg)
        result["choice"] = dlg.ShowModal()
        dlg.Destroy()
        done.set()

    wx.CallAfter(_show)
    done.wait()
    return result["choice"]

def _overwrite_local(log, project_path):
    """Discard local changes (and abort any in-progress merge), then pull origin/main."""
    merge_head = _run(["git", "rev-parse", "-q", "--verify", "MERGE_HEAD"], project_path)
    if merge_head.returncode == 0:
        log("▶ 中止未完成的合併 (git merge --abort) ...")
        r = _run(["git", "merge", "--abort"], project_path)
        if r.returncode != 0 and r.stderr.strip():
            log(f"   {r.stderr.strip()}")

    log("▶ 捨棄本地變更 (git checkout -- .) ...")
    r = _run(["git", "checkout", "--", "."], project_path)
    if r.returncode != 0:
        log(f"\n✗  捨棄本地變更失敗:\n{r.stderr.strip()}")
        return

    log("▶ 重新執行 git pull origin main ...")
    r = _run(["git", "pull", "origin", "main"], project_path)
    out = r.stdout.strip()
    err = r.stderr.strip()
    if r.returncode != 0:
        log(f"\n✗  Pull failed:\n{(out + chr(10) + err).strip()}")
        return

    if out:
        log(out)
    log("\n✓  Pull complete!（本地變更已被覆蓋）")
    if "Already up to date" not in out:
        log("\n⚠  Close and reopen the project to reload updated files.")

def _pull_fn(log, project_path):
    log("▶ Checking local status...")
    st = _run(["git", "status", "--porcelain"], project_path)
    if st.stdout.strip():
        changed = st.stdout.strip().splitlines()
        log("⚠  Uncommitted changes detected:")
        for l in changed:
            log(f"   {l}")

        msg = _build_conflict_message(
            "Pull 前偵測到尚未提交的本地變更，直接 Pull 可能會失敗或造成衝突。\n"
            "(Uncommitted local changes detected before pull.)",
            files=[l[3:] for l in changed])
        choice = _ask_conflict_dialog("發現未提交的變更 (Uncommitted Changes)", msg)
        if choice == wx.ID_YES:
            log("")
            _overwrite_local(log, project_path)
        else:
            log("\n✗  Pull 已取消（保留本地變更，請自行處理後再試）。")
        return

    log("▶ Running git pull...")
    r = _run(["git", "pull"], project_path)
    out = r.stdout.strip()
    err = r.stderr.strip()
    combined = (out + "\n" + err).strip()

    if r.returncode != 0:
        if _is_non_fast_forward(combined):
            log(f"\n✗  Pull 被拒絕：本地落後遠端 (non-fast-forward)\n{combined}")
            msg = _build_conflict_message(
                "本地分支落後於遠端，Git 拒絕以非 fast-forward 方式合併。\n"
                "(Local branch is behind the remote — pull rejected.)")
            choice = _ask_conflict_dialog("Pull 被拒絕 (Non-Fast-Forward)", msg)
            if choice == wx.ID_YES:
                log("")
                _overwrite_local(log, project_path)
            else:
                log("\n✗  Pull 已取消，請自行處理後再試。")
            return

        if _is_merge_conflict(combined):
            conflicted = _run(["git", "diff", "--name-only", "--diff-filter=U"], project_path)
            files = conflicted.stdout.strip().splitlines()
            log(f"\n✗  Pull 後發生合併衝突 (merge conflict)\n{combined}")
            if files:
                log("衝突檔案：")
                for f in files:
                    log(f"  {f}")
            msg = _build_conflict_message(
                "Pull 過程中發生合併衝突 (Merge conflict occurred during pull).",
                files=files)
            choice = _ask_conflict_dialog("發生合併衝突 (Merge Conflict)", msg)
            if choice == wx.ID_YES:
                log("")
                _overwrite_local(log, project_path)
            else:
                log("\n✗  Pull 已取消，合併衝突尚未解決，請手動處理。")
            return

        log(f"\n✗  Pull failed:\n{combined}")
        return

    log(out)
    log("\n✓  Pull complete!")
    if "Already up to date" not in out:
        log("\n⚠  Close and reopen the project to reload updated files.")

def _status_fn(log, project_path):
    log("▶ Fetching git info...\n")
    b  = _run(["git", "branch", "--show-current"], project_path)
    log(f"Branch:  {b.stdout.strip()}")
    u  = _run(["git", "remote", "get-url", "origin"], project_path)
    log(f"Remote:  {u.stdout.strip() if u.returncode == 0 else '(no remote)'}")
    sb = _run(["git", "status", "-sb"], project_path)
    first = sb.stdout.splitlines()[0] if sb.stdout else ""
    if "ahead" in first or "behind" in first:
        log(f"Sync:    {first.replace('## ', '')}")
    log("")
    st = _run(["git", "status", "--porcelain"], project_path)
    if st.stdout.strip():
        log("Uncommitted changes:")
        for l in st.stdout.strip().splitlines():
            log(f"  {l}")
    else:
        log("✓  Working tree clean")
    log("")
    lg = _run(["git", "log", "--oneline", "-8"], project_path)
    if lg.stdout.strip():
        log("Recent commits:")
        for l in lg.stdout.strip().splitlines():
            log(f"  {l}")

# ── Public entry points ───────────────────────────────────────────────────────

def run_push(project_path):
    dlg = PushDialog(project_path)
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy(); return
    commit_msg = dlg.GetMessage()
    dlg.Destroy()

    if not commit_msg.strip():
        wx.MessageBox("Commit message cannot be empty.", "Cancelled",
                      wx.OK | wx.ICON_WARNING)
        return

    try:
        import pcbnew
        board = pcbnew.GetBoard()
        pcbnew.SaveBoard(board.GetFileName(), board)
    except Exception:
        pass

    _push_fn._commit_msg = commit_msg
    op = OperationDialog("Git Push", project_path, _push_fn)
    op.ShowModal()
    op.Destroy()

def run_pull(project_path):
    confirm = wx.MessageDialog(None,
        "Pull latest changes from remote?\n\n⚠  Save your work before pulling.",
        f"{APPNAME} — Pull", wx.YES_NO | wx.ICON_QUESTION)
    center_on_screen(confirm)
    result = confirm.ShowModal()
    confirm.Destroy()
    if result != wx.ID_YES:
        return
    op = OperationDialog("Git Pull", project_path, _pull_fn)
    op.ShowModal()
    op.Destroy()

def run_status(project_path):
    op = OperationDialog("Git Status", project_path, _status_fn)
    op.ShowModal()
    op.Destroy()

def run_main_dialog(project_path):
    if not is_git_repo(project_path):
        wx.MessageBox(
            f"This project is not inside a Git repository.\n\nPath: {project_path}",
            APPNAME, wx.OK | wx.ICON_ERROR)
        return
    dlg = MainMenuDialog(project_path)
    dlg.ShowModal()
    dlg.Destroy()
