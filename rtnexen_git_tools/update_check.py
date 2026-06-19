import json
import threading
import urllib.request
import webbrowser

import wx

from .i18n import t, get_skipped_version, set_skipped_version

APPNAME = "RTnexen PPS Tool"
REPO = "RT-Next-Energy-Systems/RTnexen_PPS_Tool"
REPO_URL = f"https://github.com/{REPO}"
RELEASE_API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
README_URL = f"https://raw.githubusercontent.com/{REPO}/{{tag}}/README.md"
TIMEOUT = 8

# ── Version helpers ────────────────────────────────────────────────────────

def _parse_version(v):
    v = v.strip().lstrip("vV")
    parts = []
    for piece in v.split("."):
        digits = ""
        for ch in piece:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts)

def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "RTnexen-PPS-Tool"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)

def _fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "RTnexen-PPS-Tool"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")

def _latest_release():
    data = _fetch_json(RELEASE_API_URL)
    return data.get("tag_name", "").strip() or None

# ── Entry point ────────────────────────────────────────────────────────────

def check_for_update_async(current_version):
    """Check GitHub for a newer tag than `current_version`. No-ops silently
    if offline or on any network/API error. Shows UpdateDialog if a newer,
    non-skipped tag is found."""
    def worker():
        try:
            latest = _latest_release()
            if not latest:
                return
            if _parse_version(latest) <= _parse_version(current_version):
                return
            if get_skipped_version() == latest:
                return
            readme = _fetch_text(README_URL.format(tag=latest))
        except Exception:
            return
        wx.CallAfter(_show_update_dialog, latest, current_version, readme)
    threading.Thread(target=worker, daemon=True).start()

def _show_update_dialog(latest, current_version, readme):
    dlg = UpdateDialog(latest, current_version, readme)
    dlg.ShowModal()
    dlg.Destroy()

# ── Dialog ─────────────────────────────────────────────────────────────────

class UpdateDialog(wx.Dialog):
    def __init__(self, latest, current_version, readme):
        super().__init__(None, title=f"{APPNAME} — {t('update_available_title')}",
                          style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                          size=(640, 520))
        self.latest = latest
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(panel, label=t("update_available_msg",
                              current=current_version, latest=latest))
        sizer.Add(info, 0, wx.ALL, 14)

        text = wx.TextCtrl(panel, value=readme,
                            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        text.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE,
                              wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)

        row = wx.BoxSizer(wx.HORIZONTAL)
        update_btn = wx.Button(panel, label=t("btn_update_open"))
        update_btn.Bind(wx.EVT_BUTTON, self._on_update)
        row.Add(update_btn, 0, wx.RIGHT, 10)

        skip_btn = wx.Button(panel, label=t("btn_skip_version"))
        skip_btn.Bind(wx.EVT_BUTTON, self._on_skip)
        row.Add(skip_btn, 0, wx.RIGHT, 10)

        row.AddStretchSpacer()
        cancel_btn = wx.Button(panel, label=t("cancel"))
        cancel_btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CANCEL))
        row.Add(cancel_btn, 0)

        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 14)

        panel.SetSizer(sizer)
        self.Layout()
        self.CenterOnScreen()

    def _on_update(self, event):
        webbrowser.open(REPO_URL)
        self.EndModal(wx.ID_OK)

    def _on_skip(self, event):
        set_skipped_version(self.latest)
        self.EndModal(wx.ID_OK)
