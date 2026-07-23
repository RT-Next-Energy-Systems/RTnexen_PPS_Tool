import json
import os
import shutil
import tempfile
import threading
import urllib.request
import webbrowser
import zipfile

import wx

from .i18n import t, get_skipped_version, set_skipped_version
from .common import VERSION

APPNAME = "RTnexen PPS Tool"
REPO = "RT-Next-Energy-Systems/RTnexen_PPS_Tool"
REPO_URL = f"https://github.com/{REPO}"
RELEASE_API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
README_URL = f"https://raw.githubusercontent.com/{REPO}/{{tag}}/README.md"
ARCHIVE_URL = f"https://github.com/{REPO}/archive/refs/tags/{{tag}}.zip"
TIMEOUT = 8

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_PARENT = os.path.dirname(PLUGIN_DIR)
PLUGIN_PKG_NAME = os.path.basename(PLUGIN_DIR)

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

# ── Self-update (download + install) ──────────────────────────────────────

def _find_plugin_source(extracted_root):
    """Search the extracted archive for the plugin package folder
    (named PLUGIN_PKG_NAME and containing __init__.py)."""
    for dirpath, _dirnames, filenames in os.walk(extracted_root):
        if os.path.basename(dirpath) == PLUGIN_PKG_NAME and "__init__.py" in filenames:
            return dirpath
    return None

def download_and_install_update(tag):
    """Download the release archive for `tag`, back up the currently
    installed plugin folder, then replace it with the new version.
    Returns (True, backup_dir) on success, or (False, error_message)."""
    tmp_dir = tempfile.mkdtemp(prefix="rtnexen_update_")
    try:
        zip_path = os.path.join(tmp_dir, "release.zip")
        req = urllib.request.Request(ARCHIVE_URL.format(tag=tag),
                                      headers={"User-Agent": "RTnexen-PPS-Tool"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(zip_path, "wb") as f:
            f.write(resp.read())

        extract_dir = os.path.join(tmp_dir, "extracted")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        src = _find_plugin_source(extract_dir)
        if not src:
            return False, t("auto_update_layout_mismatch")

        backup_dir = os.path.join(PLUGINS_PARENT, f"{PLUGIN_PKG_NAME}_backup_v{VERSION}")
        if os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir)
        shutil.copytree(PLUGIN_DIR, backup_dir)

        shutil.rmtree(PLUGIN_DIR)
        shutil.copytree(src, PLUGIN_DIR)
        return True, backup_dir
    except Exception as e:
        return False, str(e)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

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

        self.status_lbl = wx.StaticText(panel, label="")
        self.status_lbl.SetForegroundColour(wx.Colour(255, 204, 77))
        sizer.Add(self.status_lbl, 0, wx.LEFT | wx.RIGHT, 14)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.auto_btn = wx.Button(panel, label=t("btn_auto_update"))
        self.auto_btn.Bind(wx.EVT_BUTTON, self._on_auto_update)
        row.Add(self.auto_btn, 0, wx.RIGHT, 10)

        self.update_btn = wx.Button(panel, label=t("btn_update_open"))
        self.update_btn.Bind(wx.EVT_BUTTON, self._on_update)
        row.Add(self.update_btn, 0, wx.RIGHT, 10)

        self.skip_btn = wx.Button(panel, label=t("btn_skip_version"))
        self.skip_btn.Bind(wx.EVT_BUTTON, self._on_skip)
        row.Add(self.skip_btn, 0, wx.RIGHT, 10)

        row.AddStretchSpacer()
        self.cancel_btn = wx.Button(panel, label=t("cancel"))
        self.cancel_btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CANCEL))
        row.Add(self.cancel_btn, 0)

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

    def _on_auto_update(self, event):
        confirm = wx.MessageDialog(
            self, t("auto_update_confirm_msg", latest=self.latest),
            f"{APPNAME} — {t('auto_update_confirm_title')}",
            wx.YES_NO | wx.ICON_WARNING)
        confirm.SetYesNoLabels(t("ok"), t("cancel"))
        proceed = confirm.ShowModal() == wx.ID_YES
        confirm.Destroy()
        if not proceed:
            return

        for btn in (self.auto_btn, self.update_btn, self.skip_btn, self.cancel_btn):
            btn.Disable()
        self.status_lbl.SetLabel(t("auto_update_downloading"))

        def worker():
            ok, info = download_and_install_update(self.latest)
            wx.CallAfter(self._auto_update_done, ok, info)
        threading.Thread(target=worker, daemon=True).start()

    def _auto_update_done(self, ok, info):
        self.status_lbl.SetLabel("")
        if ok:
            wx.MessageBox(t("auto_update_success", backup=info),
                           APPNAME, wx.OK | wx.ICON_INFORMATION)
            self.EndModal(wx.ID_OK)
        else:
            wx.MessageBox(t("auto_update_fail", err=info),
                           APPNAME, wx.OK | wx.ICON_ERROR)
            for btn in (self.auto_btn, self.update_btn, self.skip_btn, self.cancel_btn):
                btn.Enable()
