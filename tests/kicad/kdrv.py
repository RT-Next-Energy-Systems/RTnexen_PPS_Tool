"""Runs INSIDE the real pcbnew process (loaded by zz_probe.py plugin).
Drives the plugin's real dialogs like a user, records results to $HOME/result.json."""
import os, sys, json, traceback, wx, pcbnew
RES = {"steps": [], "shown": [], "logs": []}
ANSWERS = []
def done(**kw):
    RES.update(kw)
    with open(os.path.join(os.environ["HOME"], "result.json"), "w", encoding="utf-8") as f: json.dump(RES, f, ensure_ascii=False, indent=1)
    os._exit(0)

class FakeMD:
    def __init__(self, parent, message, caption="", style=0, *a, **k): self.m, self.c = message, caption
    def SetYesNoLabels(self, *a): pass
    def SetYesNoCancelLabels(self, *a): pass
    def ShowModal(self):
        RES["shown"].append([self.c, self.m])
        return ANSWERS.pop(0) if ANSWERS else wx.ID_CANCEL
    def Destroy(self): pass
    def GetSize(self): return (10, 10)
    def SetPosition(self, p): pass
wx.MessageDialog = FakeMD
wx.MessageBox = lambda m, c="", s=0, *a, **k: (RES["shown"].append([c, m]), wx.OK)[1]

FILE_PATHS = []
class FakeFD:
    def __init__(self, *a, **k): pass
    def ShowModal(self): return wx.ID_OK if FILE_PATHS else wx.ID_CANCEL
    def GetPath(self): return FILE_PATHS.pop(0)
    def Destroy(self): pass
wx.FileDialog = FakeFD

def radio_select(rb, idx):
    rb.SetSelection(idx)
    ev = wx.CommandEvent(wx.wxEVT_RADIOBOX, rb.GetId()); ev.SetEventObject(rb); ev.SetInt(idx)
    rb.GetEventHandler().ProcessEvent(ev)

def check(cb, val):
    cb.SetValue(val)
    ev = wx.CommandEvent(wx.wxEVT_CHECKBOX, cb.GetId()); ev.SetEventObject(cb); ev.SetInt(int(val))
    cb.GetEventHandler().ProcessEvent(ev)

def git_out(cwd, *args):
    import subprocess
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8").stdout.strip()

PROJ = None
def proj():
    return os.path.dirname(pcbnew.GetBoard().GetFileName())

def click(btn):
    # async: a click may open a nested modal loop; never block the driver's timer
    def _do():
        ev = wx.CommandEvent(wx.wxEVT_BUTTON, btn.GetId()); ev.SetEventObject(btn)
        btn.GetEventHandler().ProcessEvent(ev)
    wx.CallAfter(_do)
def buttons(win):
    out = []
    def walk(w):
        for c in w.GetChildren():
            if isinstance(c, wx.Button): out.append(c)
            walk(c)
    walk(win); return out
def btn_label(win, text):
    return next(b for b in buttons(win) if text in b.GetLabel())
def btn_id(win, i):
    return next(b for b in buttons(win) if b.GetId() == i)

class Driver:
    """steps: list of (dialog class name, action). Acts only on the TOP-MOST shown
    dialog (the one a user could interact with). action(dlg) returns False to retry."""
    def __init__(self, steps, timeout_s=60):
        self.steps = list(steps); self.cool = 0
        self.frame = wx.Frame(None); self.frame.Hide()
        self.t = wx.Timer(self.frame); self.frame.Bind(wx.EVT_TIMER, self.tick, self.t); self.t.Start(80)
        wx.CallLater(timeout_s * 1000, lambda: self.steps and done(error="timeout waiting for " + self.steps[0][0],
                                                                    tlw=[w.__class__.__name__ for w in wx.GetTopLevelWindows() if w.IsShown()]))
    def tick(self, e):
        if not self.steps: self.t.Stop(); return
        if self.cool > 0: self.cool -= 1; return
        shown = [w for w in wx.GetTopLevelWindows() if w.IsShown() and isinstance(w, wx.Dialog)]
        if not shown: return
        w = shown[-1]
        name, act = self.steps[0]
        if w.__class__.__name__ != name: return
        try:
            if act(w) is False: return
        except Exception:
            done(error=traceback.format_exc())
        RES["steps"].append(name); self.steps.pop(0); self.cool = 6

def op_finish(then_id, key="logs"):
    def act(d):
        if not d.close_btn.IsEnabled(): return False
        RES[key].append(d.log.GetValue())
        click(btn_id(d, then_id))
    return act

def run_plugin():
    from rtnexen_git_tools.git_main_action import GitMainAction
    a = GitMainAction(); a.defaults(); a.Run()
