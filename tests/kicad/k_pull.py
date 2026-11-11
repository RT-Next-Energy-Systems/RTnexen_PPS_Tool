# Pull with conflict (PULL_CASE=conflict) or uncommitted edit (dirty); answer PULL_ANSWER=overwrite|keep
from kdrv import *
A = proj(); ans = os.environ.get("PULL_ANSWER", "overwrite")
ANSWERS[:] = [wx.ID_YES if ans == "overwrite" else wx.ID_NO]
Driver([("MainMenuDialog", lambda d: click(btn_label(d, "Pull"))), ("PullDialog", lambda d: click(btn_id(d, wx.ID_OK))),
        ("OperationDialog", op_finish(wx.ID_OK))])
def main():
    run_plugin()
    b = open(os.path.join(A, "board.kicad_pcb"), encoding="utf-8").read()
    done(board_text=[t for t in ("TEAM", "MINE", "DIRTY", "ORIGINAL", "<<<<<<<") if t in b],
         status=git_out(A, "status", "--porcelain"), merging=os.path.exists(os.path.join(A, ".git", "MERGE_HEAD")),
         head=git_out(A, "log", "-1", "--format=%s"))
wx.CallAfter(main)
