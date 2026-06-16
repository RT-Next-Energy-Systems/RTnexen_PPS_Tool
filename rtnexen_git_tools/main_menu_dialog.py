import wx

from .i18n import t, t_en
from .common import get_dialog_size, is_git_repo, APPNAME
from .base_dialog import BaseGitDialog

# ── Main Menu Dialog ──────────────────────────────────────────────────────────
# The main menu always displays in English, regardless of the selected UI
# language — only the dialogs reached from it are translated.

class MainMenuDialog(BaseGitDialog):
    def __init__(self, project_path):
        super().__init__("", project_path,
                         size=get_dialog_size(0.42, 0.62))
        p  = self.panel
        cs = self.content_sizer

        cs.AddSpacer(20)

        for label, tip, handler, color in [
            (t_en("btn_push"),   t_en("tip_push"),   self._push,   wx.Colour(0, 119, 252)),
            (t_en("btn_pull"),   t_en("tip_pull"),   self._pull,   wx.Colour(255, 117, 31)),
            (t_en("btn_status"), t_en("tip_status"), self._status, wx.Colour(245, 219, 112)),
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
        row.Add(wx.Button(p, wx.ID_CANCEL, t_en("cancel"), size=(90, 36)), 0)
        cs.Add(row, 0, wx.EXPAND | wx.ALL, 14)
        self.FinalizeLayout()

    def _require_git(self):
        if not is_git_repo(self.project_path):
            wx.MessageBox(
                t("no_git_action", path=self.project_path),
                APPNAME, wx.OK | wx.ICON_WARNING)
            return False
        return True

    def _push(self, e):
        if not self._require_git():
            return
        self.EndModal(wx.ID_OK)
        from .git_runner import run_push
        run_push(self.project_path)

    def _pull(self, e):
        if not self._require_git():
            return
        self.EndModal(wx.ID_OK)
        from .git_runner import run_pull
        run_pull(self.project_path)

    def _status(self, e):
        if not self._require_git():
            return
        self.EndModal(wx.ID_OK)
        from .git_runner import run_status
        run_status(self.project_path)
