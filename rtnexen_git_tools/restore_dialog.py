import wx
import threading

from .i18n import t
from .common import (APPNAME, _run, get_target_configs, get_dialog_size, center_on_screen,
                     porcelain_lines, _rebase_in_progress, watch_open_board)

# ── Restore to a commit (Settings → Restore) ─────────────────────────────────
# Overwrites the LOCAL working tree with the contents of a chosen commit.
# History is never rewritten: the result is recorded as one new commit on top
# of HEAD ("Restore to <hash>: <subject>"), so a normal Push syncs it to the
# remote — no force push needed, and nothing committed is ever lost.

MAX_COMMITS = 200
_LOG_FORMAT = "%H%x1f%h%x1f%ad%x1f%an%x1f%s"
_FIELDS = ("hash", "short", "date", "author", "subject")
RED = wx.Colour(220, 60, 50)
GREY = wx.Colour(140, 140, 140)

# ── Git helpers (no UI) ──────────────────────────────────────────────────────

def list_commits(path, limit=MAX_COMMITS):
    """Latest `limit` commits reachable from HEAD, newest first."""
    r = _run(["git", "log", f"--max-count={limit}", "--date=format:%Y-%m-%d %H:%M",
              f"--format={_LOG_FORMAT}", "HEAD"], path)
    if r.returncode != 0:
        return []
    rows = []
    for line in r.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 5:
            rows.append(dict(zip(_FIELDS, parts)))
    return rows

def diff_stat(path, commit):
    """Tracked files whose content differs between the working tree and `commit`
    — i.e. exactly the files a restore would change."""
    r = _run(["git", "diff", "--stat", "--no-color", commit], path)
    return r.stdout.strip() if r.returncode == 0 else (r.stderr.strip() or r.stdout.strip())

def dirty_tracked(path):
    """`git status --porcelain` lines for tracked files with uncommitted
    changes (untracked files are not touched by a restore, so they're skipped)."""
    st = _run(["git", "status", "--porcelain"], path)
    return [l for l in porcelain_lines(st.stdout) if not l.startswith("??")]

def untracked_collisions(path, commit):
    """Untracked (non-ignored) files that have the same path as a file inside
    `commit`. A restore would silently overwrite them, so they're listed in the
    confirmation just like uncommitted changes."""
    tree = _run(["git", "ls-tree", "-r", "-z", "--name-only", commit], path)
    others = _run(["git", "ls-files", "-z", "--others", "--exclude-standard"], path)
    if tree.returncode != 0 or others.returncode != 0:
        return []
    in_commit = set(tree.stdout.split("\0"))
    return [f for f in others.stdout.split("\0") if f and f in in_commit]

def blocking_problem(path):
    """i18n key describing why a restore can't start right now, or None."""
    if not _run(["git", "branch", "--show-current"], path).stdout.strip():
        return "restore_err_detached"
    if _rebase_in_progress(path) or \
            _run(["git", "rev-parse", "-q", "--verify", "MERGE_HEAD"], path).returncode == 0:
        return "restore_err_busy"
    return None

def restore_to_commit(path, commit, short, subject):
    """Make index + working tree identical to `commit` and record that as a new
    commit. Returns ("ok" | "same" | "error", detail).

    1. read-tree --reset -u: switch index and work tree to the commit's tree
       (also deletes tracked files the commit doesn't have). Untracked files
       are left alone, except one sharing a path with a file in the commit
       (see untracked_collisions — the confirmation lists those).
    2. checkout-index -a -f: read-tree leaves a modified file alone when its
       index entry already equals the commit's, so force every tracked file
       from the index to make "overwrite local" literally true.
    3. commit the result on top of HEAD ("same" if nothing differs)."""
    r = _run(["git", "read-tree", "-u", "--reset", commit], path)
    if r.returncode != 0:
        return "error", (r.stderr.strip() or r.stdout.strip())
    r = _run(["git", "checkout-index", "-a", "-f"], path)
    if r.returncode != 0:
        return "error", (r.stderr.strip() or r.stdout.strip())
    r = _run(["git", "commit", "-F", "-"], path, input=f"Restore to {short}: {subject}")
    if r.returncode != 0:
        out = (r.stdout + "\n" + r.stderr).strip()
        if "nothing to commit" in out or "nothing added to commit" in out:
            return "same", ""
        return "error", out
    return "ok", ""

# ── Final confirmation (typed, so a stray click can't trigger it) ────────────

class _ConfirmDialog(wx.Dialog):
    def __init__(self, parent, cfg, commit, dirty):
        super().__init__(parent, title=f"{APPNAME} — {t('restore_confirm_title')}",
                         style=wx.DEFAULT_DIALOG_STYLE)
        self._short = commit["short"]
        wrap = 560
        sizer = wx.BoxSizer(wx.VERTICAL)

        head = wx.StaticText(self, label=t("restore_confirm_head"))
        head.SetForegroundColour(RED)
        head.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(head, 0, wx.ALL, 14)

        body = wx.StaticText(self, label=t(
            "restore_confirm_body", target=cfg["name"], path=cfg["path"],
            short=commit["short"], date=commit["date"], subject=commit["subject"]))
        body.Wrap(wrap)
        sizer.Add(body, 0, wx.LEFT | wx.RIGHT, 14)

        if dirty:
            shown = [f"  {l}" for l in dirty[:10]]
            if len(dirty) > 10:
                shown.append(t("restore_confirm_more", n=len(dirty) - 10))
            warn = wx.StaticText(self, label=t(
                "restore_confirm_dirty", n=len(dirty), files="\n".join(shown)))
            warn.SetForegroundColour(RED)
            warn.Wrap(wrap)
            sizer.Add(warn, 0, wx.LEFT | wx.RIGHT | wx.TOP, 14)

        prompt = wx.StaticText(self, label=t("restore_confirm_type", short=self._short))
        prompt.Wrap(wrap)
        sizer.Add(prompt, 0, wx.LEFT | wx.RIGHT | wx.TOP, 14)
        self.entry = wx.TextCtrl(self)
        self.entry.Bind(wx.EVT_TEXT, self._on_text)
        sizer.Add(self.entry, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        self.ok_btn = wx.Button(self, wx.ID_OK, t("btn_restore_confirm"))
        self.ok_btn.SetForegroundColour(RED)
        self.ok_btn.Disable()  # enabled only once the commit id is typed correctly
        row.Add(self.ok_btn, 0, wx.RIGHT, 10)
        cancel = wx.Button(self, wx.ID_CANCEL, t("cancel"))
        cancel.SetDefault()  # Enter / Esc = safe choice
        row.Add(cancel, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 14)

        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.Fit()
        center_on_screen(self)
        self.entry.SetFocus()

    def _on_text(self, event):
        self.ok_btn.Enable(self.entry.GetValue().strip().lower() == self._short.lower())

# ── Restore dialog ───────────────────────────────────────────────────────────

class RestoreDialog(wx.Dialog):
    def __init__(self, parent, project_path):
        super().__init__(parent, title=f"{APPNAME} — {t('restore_title')}",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                         size=get_dialog_size(0.5, 0.7))
        self.targets = get_target_configs(project_path)
        self._commits = []
        self._load_token = 0
        self._diff_token = 0

        sizer = wx.BoxSizer(wx.VERTICAL)

        warn = wx.StaticText(self, label=t("restore_warning_bar"))
        warn.SetForegroundColour(RED)
        sizer.Add(warn, 0, wx.ALL, 12)

        self.target_radio = None
        if len(self.targets) > 1:
            self.target_radio = wx.RadioBox(
                self, label=t("target"), choices=[c["name"] for c in self.targets],
                majorDimension=len(self.targets), style=wx.RA_SPECIFY_COLS)
            self.target_radio.Bind(wx.EVT_RADIOBOX, lambda e: self._load_commits())
            sizer.Add(self.target_radio, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for i, (key, width) in enumerate((("restore_col_commit", 110), ("restore_col_date", 140),
                                          ("restore_col_author", 120), ("restore_col_message", 420))):
            self.list.InsertColumn(i, t(key), width=width)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self.list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_deselect)
        sizer.Add(self.list, 3, wx.EXPAND | wx.ALL, 12)

        self.note = wx.StaticText(self, label="")
        self.note.SetForegroundColour(GREY)
        sizer.Add(self.note, 0, wx.LEFT | wx.RIGHT, 12)

        sizer.Add(wx.StaticText(self, label=t("restore_diff_label")),
                  0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.diff = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self.diff.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE,
                                  wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.diff, 2, wx.EXPAND | wx.ALL, 12)

        row = wx.BoxSizer(wx.HORIZONTAL)
        close_btn = wx.Button(self, wx.ID_CANCEL, t("close"), size=(100, 32))
        close_btn.SetDefault()
        row.Add(close_btn, 0)
        row.AddStretchSpacer()
        self.restore_btn = wx.Button(self, label=t("btn_restore_apply"), size=(-1, 32))
        self.restore_btn.SetForegroundColour(RED)
        self.restore_btn.Disable()  # nothing selected yet
        self.restore_btn.Bind(wx.EVT_BUTTON, self._on_restore)
        row.Add(self.restore_btn, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.Layout()
        center_on_screen(self)
        wx.CallAfter(self._load_commits)

    def _cfg(self):
        idx = self.target_radio.GetSelection() if self.target_radio else 0
        return self.targets[max(idx, 0)]

    def _load_commits(self):
        self._load_token += 1
        self._diff_token += 1
        token = self._load_token
        path = self._cfg()["path"]
        self._commits = []
        self.list.DeleteAllItems()
        self.diff.SetValue("")
        self.restore_btn.Disable()
        self.note.SetLabel(t("loading"))

        def worker():
            rows = list_commits(path)
            wx.CallAfter(self._fill, token, rows)
        threading.Thread(target=worker, daemon=True).start()

    def _fill(self, token, rows):
        if not self or token != self._load_token:
            return
        self._commits = rows
        for i, c in enumerate(rows):
            short = c["short"] + (t("restore_current_mark") if i == 0 else "")
            idx = self.list.InsertItem(i, short)
            self.list.SetItem(idx, 1, c["date"])
            self.list.SetItem(idx, 2, c["author"])
            self.list.SetItem(idx, 3, c["subject"])
        if not rows:
            self.note.SetLabel(t("restore_no_commits"))
        elif len(rows) >= MAX_COMMITS:
            self.note.SetLabel(t("restore_limit_note", n=MAX_COMMITS))
        else:
            self.note.SetLabel("")

    def _on_select(self, event):
        idx = event.GetIndex()
        if idx < 0 or idx >= len(self._commits):
            return
        self.restore_btn.Enable()
        self._diff_token += 1
        token = self._diff_token
        path = self._cfg()["path"]
        commit = self._commits[idx]["hash"]
        self.diff.SetValue(t("loading"))

        def worker():
            text = diff_stat(path, commit)
            lines = text.splitlines()
            if len(lines) > 80:
                lines = lines[:80] + ["..."]
            wx.CallAfter(self._show_diff, token, "\n".join(lines) or t("restore_diff_none"))
        threading.Thread(target=worker, daemon=True).start()

    def _show_diff(self, token, text):
        if self and token == self._diff_token:
            self.diff.SetValue(text)

    def _on_deselect(self, event):
        if self.list.GetFirstSelected() < 0:
            self.restore_btn.Disable()
            self.diff.SetValue("")

    def _on_restore(self, event):
        idx = self.list.GetFirstSelected()
        if idx < 0 or idx >= len(self._commits):
            return
        commit = self._commits[idx]
        cfg = self._cfg()
        path = cfg["path"]

        problem = blocking_problem(path)
        if problem:
            wx.MessageBox(t(problem), APPNAME, wx.OK | wx.ICON_ERROR)
            return

        at_risk = dirty_tracked(path) + [f"?? {f}" for f in untracked_collisions(path, commit["hash"])]
        dlg = _ConfirmDialog(self, cfg, commit, at_risk)
        confirmed = dlg.ShowModal() == wx.ID_OK
        dlg.Destroy()
        if not confirmed:
            return

        # watch_open_board: if this rewrote the PCB open in the editor, mark the
        # in-memory board stale so the next Push won't auto-save the OLD board
        # over the restored file.
        wx.BeginBusyCursor()
        try:
            kind, detail = watch_open_board(
                lambda: restore_to_commit(path, commit["hash"], commit["short"], commit["subject"]))
        finally:
            wx.EndBusyCursor()

        if kind == "ok":
            wx.MessageBox(t("restore_done", short=commit["short"]), APPNAME,
                          wx.OK | wx.ICON_INFORMATION)
        elif kind == "same":
            wx.MessageBox(t("restore_done_same", short=commit["short"]), APPNAME,
                          wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(t("restore_fail", err=detail), APPNAME, wx.OK | wx.ICON_ERROR)
        self._load_commits()
