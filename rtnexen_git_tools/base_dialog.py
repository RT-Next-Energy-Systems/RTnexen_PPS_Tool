import wx
import threading

from .i18n import t, get_language
from .common import VERSION, APPNAME, ID_BACK, _run, get_dialog_size, center_on_screen
from .settings_dialog import SettingsDialog

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

        lbl_text = f"{APPNAME}  —  {subtitle}" if subtitle else APPNAME
        lbl = wx.StaticText(hdr, label=lbl_text)
        lbl.SetForegroundColour(self.CYAN)
        lbl.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        hs.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 14)
        hs.AddStretchSpacer()

        self.branch_lbl = wx.StaticText(hdr, label="⎇  ...  ")
        self.branch_lbl.SetForegroundColour(self.GREEN)
        self.branch_lbl.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        hs.Add(self.branch_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        vlbl = wx.StaticText(hdr, label=f"v{VERSION}")
        vlbl.SetForegroundColour(self.DIM)
        hs.Add(vlbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        sbtn = wx.Button(hdr, label="⚙", size=(32, 32))
        sbtn.SetToolTip(t("settings"))
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
            branch = r.stdout.strip() or t("branch_unknown")
            wx.CallAfter(self._set_branch, branch)
        threading.Thread(target=worker, daemon=True).start()

    def _set_branch(self, branch):
        if self.branch_lbl:
            self.branch_lbl.SetLabel(f"⎇  {branch}  ")

    def _on_settings(self, event):
        old_lang = get_language()
        dlg = SettingsDialog(self.project_path)
        dlg.ShowModal()
        dlg.Destroy()
        if get_language() != old_lang:
            wx.MessageBox(t("lang_changed_reopen"), APPNAME, wx.OK | wx.ICON_INFORMATION)

    def FinalizeLayout(self):
        self.panel.Layout()
        self.Layout()
        self.Fit()
        cur_w, cur_h = self.GetSize()
        min_w, min_h = self.GetMinSize()
        self.SetSize((max(cur_w, min_w), max(cur_h, min_h)))
        center_on_screen(self)

    def add_bottom_buttons(self, ok_label=None, show_cancel=True):
        if ok_label is None:
            ok_label = t("ok")
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.back_btn = wx.Button(self.panel, ID_BACK, t("back"), size=(100, 36))
        self.back_btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(ID_BACK))
        row.Add(self.back_btn, 0, wx.RIGHT, 10)
        row.AddStretchSpacer()
        ok = wx.Button(self.panel, wx.ID_OK, ok_label, size=(120, 36))
        ok.SetDefault()
        row.Add(ok, 0, wx.RIGHT, 10)
        if show_cancel:
            row.Add(wx.Button(self.panel, wx.ID_CANCEL, t("cancel"), size=(90, 36)), 0)
        self.content_sizer.Add(row, 0, wx.EXPAND | wx.ALL, 12)
        return ok
