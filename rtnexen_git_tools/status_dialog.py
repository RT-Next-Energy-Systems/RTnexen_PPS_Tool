import wx
import threading

from .i18n import t, t_en
from .common import _run, is_git_repo, get_target_configs, get_dialog_size, untrack_ignored_files
from .base_dialog import BaseGitDialog

# Status indicator dot colors shown as an icon on each StatusDialog tab:
#   green  — clean working tree, in sync with remote (nothing to push/pull)
#   yellow — uncommitted local changes
#   red    — working tree clean, but local commits not yet pushed
#   grey   — unknown / not a git repo
# Drawn as small bitmaps (rather than emoji) because native wx.Notebook tabs
# on Windows render color emoji as monochrome fallback glyphs.
STATUS_DOT_COLORS = {
    "clean": wx.Colour(76, 175, 80),
    "dirty": wx.Colour(255, 204, 77),
    "unpushed": wx.Colour(229, 57, 53),
    None: wx.Colour(120, 120, 120),
}

def _make_dot_bitmap(color, size=16):
    bmp = wx.Bitmap(size, size, 32)
    bmp.UseAlpha()
    dc = wx.MemoryDC(bmp)
    dc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0)))
    dc.Clear()
    gc = wx.GraphicsContext.Create(dc)
    gc.SetBrush(wx.Brush(color))
    gc.SetPen(wx.TRANSPARENT_PEN)
    margin = 3
    gc.DrawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
    dc.SelectObject(wx.NullBitmap)
    return bmp

# ── Status Dialog (tabbed per-target view) ──────────────────────────────────

class StatusDialog(BaseGitDialog):
    def __init__(self, project_path):
        super().__init__(t_en("subtitle_status"), project_path,
                         size=get_dialog_size(0.5, 0.65))
        p  = self.panel
        cs = self.content_sizer

        self.targets = get_target_configs(project_path)

        self.notebook = wx.Notebook(p)
        self.logs = []
        for cfg in self.targets:
            page = wx.Panel(self.notebook)
            page_sizer = wx.BoxSizer(wx.VERTICAL)
            log_ctrl = wx.TextCtrl(page,
                style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL | wx.TE_RICH2)
            log_ctrl.SetFont(
                wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            log_ctrl.SetBackgroundColour(wx.Colour(20, 20, 28))
            log_ctrl.SetForegroundColour(wx.Colour(220, 220, 220))
            log_ctrl.SetValue(t("loading"))
            page_sizer.Add(log_ctrl, 1, wx.EXPAND | wx.ALL, 8)
            page.SetSizer(page_sizer)
            self.notebook.AddPage(page, cfg["name"])
            self.logs.append(log_ctrl)

        self.image_list = wx.ImageList(16, 16)
        self.icon_idx = {
            kind: self.image_list.Add(_make_dot_bitmap(color))
            for kind, color in STATUS_DOT_COLORS.items()
        }
        self.notebook.AssignImageList(self.image_list)

        cs.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 12)

        self.gauge = wx.Gauge(p, range=100, size=(-1, 8))
        cs.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.close_btn = self.add_bottom_buttons(t("close"), show_cancel=False)
        self.close_btn.Disable()
        self.back_btn.Disable()

        self.FinalizeLayout()
        wx.CallAfter(self._start)

    def _start(self):
        self.gauge.Pulse()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        for i, cfg in enumerate(self.targets):
            def log(msg, idx=i):
                wx.CallAfter(self._append, idx, msg)
            kind = _status_fn(log, cfg["path"], cfg["name"])
            wx.CallAfter(self._set_tab_icon, i, kind)
        wx.CallAfter(self._finish)

    def _append(self, idx, msg):
        ctrl = self.logs[idx]
        if ctrl:
            if ctrl.GetValue() == t("loading"):
                ctrl.SetValue("")
            ctrl.AppendText(msg + "\n")

    def _set_tab_icon(self, idx, kind):
        if not self.notebook:
            return
        self.notebook.SetPageImage(idx, self.icon_idx.get(kind, self.icon_idx[None]))

    def _finish(self):
        if self.gauge:
            self.gauge.SetValue(100)
        if self.close_btn:
            self.close_btn.Enable()
            self.close_btn.SetDefault()
            self.close_btn.SetFocus()
        if self.back_btn:
            self.back_btn.Enable()

# ── Git status reporting (run in background thread) ──────────────────────────

def _status_fn(log, path, name):
    log(t("status_fetching", name=name))
    if not is_git_repo(path):
        log(t("status_not_repo", path=path))
        return None

    log(t("status_path", path=path))
    branch = _run(["git", "branch", "--show-current"], path).stdout.strip()
    log(t("status_branch", branch=branch))

    u = _run(["git", "remote", "get-url", "origin"], path)
    log(t("status_remote", url=u.stdout.strip() if u.returncode == 0 else t("status_no_remote")))

    sb = _run(["git", "status", "-sb"], path)
    first = sb.stdout.splitlines()[0] if sb.stdout else ""
    ahead = "ahead" in first
    if ahead or "behind" in first:
        log(t("status_sync", info=first.replace('## ', '')))
    log("")

    # Untrack files that are now ignored; also explicitly handle .history which
    # may be a nested git dir (not caught by --ignored flag on some git versions)
    untrack_ignored_files(path)
    tracked_history = _run(["git", "ls-files", "--cached", "--", ".history"], path)
    if tracked_history.stdout.strip():
        _run(["git", "rm", "-r", "--cached", "--", ".history"], path)
    st = _run(["git", "status", "--porcelain"], path)
    if st.stdout.strip():
        log(t("status_uncommitted"))
        for l in st.stdout.strip().splitlines():
            log(f"  {l}")
        kind = "dirty"
    else:
        log(t("status_clean"))
        kind = "unpushed" if ahead else "clean"
    log("")

    lg = _run(["git", "log", "--oneline", "-8"], path)
    if lg.stdout.strip():
        log(t("status_recent_commits"))
        for l in lg.stdout.strip().splitlines():
            log(f"  {l}")

    return kind
