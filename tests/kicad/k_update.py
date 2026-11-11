# Settings -> Check for Updates -> Auto Update, through the real UI inside real pcbnew
from kdrv import *
from rtnexen_git_tools import update_check as uc
B = "http://127.0.0.1:%s" % os.environ["PPS_UPDATE_PORT"]
uc.RELEASE_API_URL = B + "/api.json"; uc.README_URL = B + "/README.md?{tag}"; uc.ARCHIVE_URL = B + "/{tag}.zip"
ANSWERS[:] = [wx.ID_YES]       # confirm auto-update
def settings_act(d):
    if not getattr(d, "_drv_clicked", False):
        d._drv_clicked = True; click(btn_label(d, "檢查更新"))
    return None
Driver([
    ("MainMenuDialog", lambda d: click(btn_label(d, "⚙"))),
    ("SettingsDialog", lambda d: click(btn_label(d, "檢查更新"))),
    ("UpdateDialog",   lambda d: click(btn_label(d, "自動更新"))),
])
def finish_when_done():
    # after the update finished (success MessageBox recorded) close everything
    if not any("更新完成" in m or "失敗" in m for c, m in RES["shown"]):
        wx.CallLater(300, finish_when_done); return
    done(plugin_dir=uc.PLUGIN_DIR, plugins_dir_entries=sorted(os.listdir(uc.PLUGINS_PARENT)),
         backups_dir=sorted(os.listdir(os.path.join(os.environ["HOME"], ".rtnexen_pps_tool", "backups"))) if os.path.isdir(os.path.join(os.environ["HOME"], ".rtnexen_pps_tool", "backups")) else [])
wx.CallAfter(run_plugin); wx.CallLater(1000, finish_when_done)
