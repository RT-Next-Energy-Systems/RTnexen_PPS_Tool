# Pull (teammate changed the board) -> Push, all through the real plugin UI inside real pcbnew
from kdrv import *
import subprocess
from rtnexen_git_tools.common import ID_BACK
A = os.path.dirname(pcbnew.GetBoard().GetFileName())
RES["board_in_editor_before"] = [d.GetText() for d in pcbnew.GetBoard().GetDrawings() if isinstance(d, pcbnew.PCB_TEXT)]
def push_act(d):
    d.msg_ctrls["project"].SetValue("k3 push after pull"); click(btn_id(d, wx.ID_OK))
Driver([
    ("MainMenuDialog", lambda d: click(btn_label(d, "Pull"))),
    ("PullDialog",     lambda d: click(btn_id(d, wx.ID_OK))),
    ("OperationDialog", op_finish(ID_BACK)),
    ("MainMenuDialog", lambda d: click(btn_label(d, "Push"))),
    ("PushDialog",     push_act),
    ("OperationDialog", op_finish(wx.ID_OK)),
])
def main():
    run_plugin()
    remote = subprocess.run(["git", "show", "origin/main:board.kicad_pcb"], cwd=A, capture_output=True, text=True).stdout
    subprocess.run(["git", "fetch", "-q"], cwd=A)
    remote = subprocess.run(["git", "show", "origin/main:board.kicad_pcb"], cwd=A, capture_output=True, text=True).stdout
    done(remote_has_TEAM=("TEAM" in remote), remote_has_ORIGINAL=("ORIGINAL" in remote),
         remote_log=subprocess.run(["git", "log", "--format=%s", "origin/main"], cwd=A, capture_output=True, text=True).stdout)
wx.CallAfter(main)
