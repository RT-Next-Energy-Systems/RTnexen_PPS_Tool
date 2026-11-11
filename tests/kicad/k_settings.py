# Settings: Remote1 name, Remote2 global, scope switch drafts, save, export/import, unsaved prompt; then Push shows ALL
from kdrv import *
A = proj(); LIB = os.path.join(os.path.dirname(A), "lib"); EXP = os.path.join(os.environ["HOME"], "export.json")
def settings_act(d):
    if d.url1_ctrl.GetValue() == "載入中...": return False
    RES["url1_loaded"] = d.url1_ctrl.GetValue()
    d.name1_ctrl.SetValue("主板專案")
    d.name2_ctrl.SetValue("元件庫"); d.path2_ctrl.SetValue(LIB)           # global scope (default)
    radio_select(d.scope_radio, 0)                                      # -> project scope
    RES["project_scope_fields"] = [d.name2_ctrl.GetValue(), d.path2_ctrl.GetValue()]
    d.name2_ctrl.SetValue("PROJ-ONLY")
    radio_select(d.scope_radio, 1)                                      # -> back to global
    RES["global_restored"] = [d.name2_ctrl.GetValue(), d.path2_ctrl.GetValue() == LIB]
    ANSWERS[:] = [wx.ID_NO,          # Back with unsaved changes -> "Stay"
                  wx.ID_YES,         # global change confirmation on Save
                  ]
    click(btn_id(d, wx.ID_CANCEL))                                       # Back -> unsaved prompt -> stay
    def save():
        RES["still_open_after_stay"] = d.IsShown()
        FILE_PATHS[:] = [EXP]
        click(btn_label(d, "匯出"))
        wx.CallLater(600, lambda: click(btn_id(d, wx.ID_SAVE)))
    wx.CallLater(600, save)
def push_act(d):
    RES["push_targets"] = [d.target_radio.GetString(i) for i in range(d.target_radio.GetCount())]
    click(btn_id(d, wx.ID_CANCEL))
Driver([("MainMenuDialog", lambda d: click(btn_label(d, "⚙"))), ("SettingsDialog", settings_act),
        ("MainMenuDialog", lambda d: click(btn_label(d, "Push"))), ("PushDialog", push_act)], timeout_s=90)
def main():
    run_plugin()
    from rtnexen_git_tools import i18n
    i18n._cache = None
    import json
    done(remote1name=git_out(A, "config", "--get", "rtnexen.remote1name"),
         scope=git_out(A, "config", "--get", "rtnexen.remote2scope"),
         project_remote2name=git_out(A, "config", "--get", "rtnexen.remote2name"),
         global_remote2=list(i18n.get_global_remote2()),
         export_has=json.load(open(EXP, encoding="utf-8")).get("remote2_name") if os.path.exists(EXP) else None)
wx.CallAfter(main)
