import wx
import threading

from .i18n import t
from .common import ID_BACK, get_dialog_size
from .base_dialog import BaseGitDialog

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
        self.back_btn = wx.Button(p, ID_BACK, t("back"), size=(100, 36))
        self.back_btn.Disable()
        self.back_btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(ID_BACK))
        row.Add(self.back_btn, 0, wx.RIGHT, 10)
        row.AddStretchSpacer()
        self.close_btn = wx.Button(p, wx.ID_OK, t("close"), size=(120, 36))
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
        if self.back_btn:
            self.back_btn.Enable()
