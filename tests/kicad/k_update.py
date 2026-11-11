# Auto-update inside real pcbnew.
#  UPDATE_MODE=auto   : opening the plugin triggers the automatic check -> UpdateDialog pops up by itself
#  UPDATE_MODE=manual : v9.9.9 is marked "skipped", so NO automatic popup; Settings -> Check for Updates still offers it
from kdrv import *
from rtnexen_git_tools import update_check as uc, i18n
B = "http://127.0.0.1:%s" % os.environ["PPS_UPDATE_PORT"]
uc.RELEASE_API_URL = B + "/api.json"; uc.README_URL = B + "/README.md?{tag}"; uc.ARCHIVE_URL = B + "/{tag}.zip"
MODE = os.environ.get("UPDATE_MODE", "auto")
ANSWERS[:] = [wx.ID_YES]       # confirm auto-update
if MODE == "manual":
    i18n.set_skipped_version("v9.9.9")
    steps = [("MainMenuDialog", lambda d: (wx.CallLater(2500, lambda: click(btn_label(d, "⚙"))), None)[1]),
             ("SettingsDialog", lambda d: click(btn_label(d, "檢查更新"))),
             ("UpdateDialog",   lambda d: click(btn_label(d, "自動更新")))]
else:
    steps = [("UpdateDialog",   lambda d: click(btn_label(d, "自動更新")))]
Driver(steps)
def finish_when_done():
    if not any("更新完成" in m or "自動更新失敗" in m for c, m in RES["shown"]):
        wx.CallLater(300, finish_when_done); return
    bdir = os.path.join(os.environ["HOME"], ".rtnexen_pps_tool", "backups")
    done(mode=MODE, plugin_dir=uc.PLUGIN_DIR, plugins_dir_entries=sorted(os.listdir(uc.PLUGINS_PARENT)),
         backups_dir=sorted(os.listdir(bdir)) if os.path.isdir(bdir) else [])
wx.CallAfter(run_plugin); wx.CallLater(1000, finish_when_done)
