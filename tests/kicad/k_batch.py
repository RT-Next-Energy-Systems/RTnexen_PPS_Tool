from kdrv import *
A = proj(); ROOT = os.path.join(os.environ["HOME"], "batchroot")
import subprocess
def sh(c, cwd): subprocess.run(c, cwd=cwd, shell=True, check=True, capture_output=True)
os.makedirs(ROOT); sh("git init -q --bare -b main r1.git && git init -q --bare -b main r2.git", os.path.dirname(ROOT))
for n in ("r1", "r2"):
    sh(f"git clone -q ../{n}.git {n}", ROOT); p = os.path.join(ROOT, n)
    sh("git checkout -q -b main && echo a > f.txt && git add . && git commit -qm init && git push -q -u origin main", p)
open(os.path.join(ROOT, "r1", "change.txt"), "w").write("c")
os.makedirs(os.path.join(ROOT, "not_a_repo"))
def settings_act(d):
    if d.url1_ctrl.GetValue() == "載入中...": return False
    d.batch_root_ctrl.SetValue(ROOT)
    ANSWERS[:] = [wx.ID_YES]                 # batch push confirm
    click(btn_label(d, "批次 Push") if any("批次 Push" in b.GetLabel() for b in buttons(d)) else [b for b in buttons(d) if "Push" in b.GetLabel()][0])
def op1(d):
    if not d.close_btn.IsEnabled(): return False
    RES["batch_push_log"] = d.log.GetValue()[-400:]
    click(btn_id(d, wx.ID_OK))
    def pull():
        s = [w for w in wx.GetTopLevelWindows() if w.__class__.__name__ == "SettingsDialog"][0]
        ANSWERS[:] = [wx.ID_YES]
        click([b for b in buttons(s) if "Pull" in b.GetLabel()][0])
    wx.CallLater(500, pull)
def op2(d):
    if not d.close_btn.IsEnabled(): return False
    RES["batch_pull_log"] = d.log.GetValue()[-400:]
    click(btn_id(d, wx.ID_OK))
    wx.CallLater(500, lambda: click(btn_id([w for w in wx.GetTopLevelWindows() if w.__class__.__name__ == "SettingsDialog"][0], wx.ID_OK)))
Driver([("MainMenuDialog", lambda d: click(btn_label(d, "⚙"))), ("SettingsDialog", settings_act),
        ("OperationDialog", op1), ("OperationDialog", op2),
        ("MainMenuDialog", lambda d: click(btn_id(d, wx.ID_CANCEL)))], timeout_s=90)
def main():
    run_plugin()
    done(r1_remote=git_out(os.path.join(ROOT, "r1"), "log", "-1", "--format=%s", "origin/main"))
wx.CallAfter(main)
