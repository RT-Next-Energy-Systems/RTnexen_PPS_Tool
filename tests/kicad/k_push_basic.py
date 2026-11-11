from kdrv import *
A = proj(); open(os.path.join(A, "新增筆記.txt"), "w", encoding="utf-8").write("x")
def push_act(d):
    RES["changed_files_box"] = d.status_text.GetValue() if d.status_text.GetValue() != "載入中..." else None
    if RES["changed_files_box"] is None: return False
    d.msg_ctrls["project"].SetValue("更新 PCB 佈局"); click(btn_id(d, wx.ID_OK))
Driver([("MainMenuDialog", lambda d: click(btn_label(d, "Push"))), ("PushDialog", push_act), ("OperationDialog", op_finish(wx.ID_OK))])
def main():
    run_plugin(); git_out(A, "fetch", "-q")
    done(remote_head=git_out(A, "log", "-1", "--format=%s", "origin/main"), remote_files=git_out(A, "ls-tree", "--name-only", "origin/main"),
         clean=git_out(A, "status", "--porcelain") == "")
wx.CallAfter(main)
