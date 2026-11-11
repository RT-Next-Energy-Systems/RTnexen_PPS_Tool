from kdrv import *
A = proj()
ANSWERS[:] = [wx.ID_NO,      # close-confirm: "Save"
              wx.ID_YES]     # clear-confirm: OK
def type_cancel(d):
    d.msg_ctrls["project"].SetValue("半成品訊息")
    RES["before_cancel"] = [d._draft_state("project"), d._has_unsaved_drafts(), d.msg_ctrls["project"].GetValue()]
    click(btn_id(d, wx.ID_CANCEL))
def reopen(d):
    RES["restored"] = d.msg_ctrls["project"].GetValue()
    clear = [b for b in buttons(d.msg_panels["project"]) if b.GetLabel() == "清除"][0]
    click(clear)
    def after():
        RES["after_clear"] = d.msg_ctrls["project"].GetValue(); click(btn_id(d, wx.ID_CANCEL))
    wx.CallLater(500, after)
Driver([("MainMenuDialog", lambda d: click(btn_label(d, "Push"))), ("PushDialog", type_cancel)])
def main():
    run_plugin()
    from rtnexen_git_tools.i18n import get_commit_draft
    RES["draft_saved"] = get_commit_draft(A)
    Driver([("MainMenuDialog", lambda d: click(btn_label(d, "Push"))), ("PushDialog", reopen)])
    run_plugin()
    done(draft_after_clear=get_commit_draft(A))
wx.CallAfter(main)
