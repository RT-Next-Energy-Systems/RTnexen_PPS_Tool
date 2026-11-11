from kdrv import *
A = proj(); BLOCK = os.environ.get("OV_BLOCK") == "1"
open(os.path.join(A, "notes.txt"), "w").write("mine")
if BLOCK:
    import time; open(os.path.join(A, "top.kicad_sch"), "w").write("(kicad_sch)"); time.sleep(0.05)
    open(os.path.join(A, "_autosave-top.kicad_sch"), "w").write("(kicad_sch unsaved)")
    ANSWERS[:] = [wx.ID_YES]            # generic "unsaved files, continue anyway?" before the dialog
else:
    ANSWERS[:] = [wx.ID_YES]            # final "overwrite remote?" confirmation
def push_act(d):
    d.msg_ctrls["project"].SetValue("overwrite!"); check(d.overwrite_chk, True)
    RES["ok_label"] = d.ok_btn.GetLabel(); RES["hint_shown"] = d.overwrite_hint.IsShown()
    click(btn_id(d, wx.ID_OK))
steps = [("MainMenuDialog", lambda d: click(btn_label(d, "Push"))), ("PushDialog", push_act)]
if not BLOCK: steps.append(("OperationDialog", op_finish(wx.ID_OK)))
Driver(steps)
def main():
    run_plugin(); git_out(A, "fetch", "-q")
    from rtnexen_git_tools.i18n import get_commit_draft
    done(remote_log=git_out(A, "log", "--format=%s", "origin/main").splitlines(), draft=get_commit_draft(A))
wx.CallAfter(main)
