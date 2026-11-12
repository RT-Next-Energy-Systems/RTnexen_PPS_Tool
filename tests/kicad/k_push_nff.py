# teammate pushed; user edits another file -> push rejected -> "Pull & Push" (NFF_MODE=pull_push) or "Skip" (NFF_MODE=skip)
from kdrv import *
A = proj(); MODE = os.environ.get("NFF_MODE", "pull_push")
open(os.path.join(A, "notes.txt"), "w").write("mine")
ANSWERS[:] = [wx.ID_YES] if MODE == "pull_push" else [wx.ID_NO]
def push_act(d):
    d.msg_ctrls["project"].SetValue("nff " + MODE); click(btn_id(d, wx.ID_OK))
Driver([("MainMenuDialog", lambda d: click(btn_label(d, "Push"))), ("PushDialog", push_act), ("OperationDialog", op_finish(wx.ID_OK))])
def main():
    run_plugin(); git_out(A, "fetch", "-q")
    done(remote_log=git_out(A, "log", "--format=%s", "origin/main").splitlines(), rebase_left=os.path.isdir(os.path.join(A, ".git", "rebase-merge")))
wx.CallAfter(main)
