"""Test harness: real wxPython (under Xvfb), stub pcbnew, scripted dialog answers."""
import os, sys, types, tempfile, subprocess, threading, shutil
ROOT = os.environ.get("PPS_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = tempfile.mkdtemp(prefix="ppshome_")
os.environ["HOME"] = HOME
os.environ["USERPROFILE"] = HOME   # Windows: expanduser("~") reads USERPROFILE
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
os.environ.pop("GIT_TERMINAL_PROMPT", None)
for k in [k for k in os.environ if k.startswith("GIT_CONFIG_")]: os.environ.pop(k)
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

class _AP:
    def register(self): pass
BOARD = {"file": ""}
SAVED = []
class _Board:
    def GetFileName(self): return BOARD["file"]
pcb = types.ModuleType("pcbnew")
pcb.ActionPlugin = _AP
pcb.GetBoard = lambda: _Board()
def _save(fn, b):
    SAVED.append(fn)
    with open(fn, "w") as f: f.write("(kicad_pcb STALE-IN-MEMORY)\n")
pcb.SaveBoard = _save
sys.modules["pcbnew"] = pcb

import wx
app = wx.App(False)

ANSWERS = []      # queue of return values for MessageDialog.ShowModal
SHOWN = []        # (title, message) of every dialog / MessageBox shown
UNEXPECTED = []   # dialogs shown with no scripted answer (answered Cancel)
_RealMD = wx.MessageDialog
class FakeMD:
    def __init__(self, parent, message, caption="", style=0, *a, **k):
        self.message, self.caption = message, caption
    def SetYesNoLabels(self, *a): pass
    def SetYesNoCancelLabels(self, *a): pass
    def ShowModal(self):
        SHOWN.append((self.caption, self.message))
        if not ANSWERS:
            # Never raise here: this runs via CallAfter while a worker thread
            # waits for the answer, so an exception would hang the test forever.
            UNEXPECTED.append(self.caption)
            return wx.ID_CANCEL
        return ANSWERS.pop(0)
    def Destroy(self): pass
    def GetSize(self): return (10, 10)
    def SetPosition(self, p): pass
wx.MessageDialog = FakeMD
def fake_box(msg, caption="", style=0, *a, **k):
    SHOWN.append((caption, msg)); return wx.OK
wx.MessageBox = fake_box

from rtnexen_git_tools import common, i18n
i18n.set_language("en")

def run_worker(fn, *args):
    """Run fn in a worker thread while pumping the wx event loop (needed for
    the CallAfter + Event.wait dialog pattern). Returns fn's result."""
    out = {}
    def w():
        try: out["r"] = fn(*args)
        except BaseException as e: out["e"] = e
    th = threading.Thread(target=w, daemon=True); th.start()
    import time
    while th.is_alive():
        app.Yield(True); time.sleep(0.005)
    app.Yield(True)
    if "e" in out: raise out["e"]
    return out.get("r")

LOG = []
def log(m): LOG.append(m)

def sh(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, encoding="utf-8", errors="replace")
    return r

def mkrepos():
    """bare remote + two clones (a = user under test, b = teammate)."""
    base = tempfile.mkdtemp(prefix="ppsrepo_")
    sh("git init -q --bare -b main remote.git", base)
    for c in ("a", "b"):
        sh(f"git clone -q remote.git {c}", base)
        sh("git config user.email t@t; git config user.name T; git checkout -q -b main 2>/dev/null || true", os.path.join(base, c))
    a, b = os.path.join(base, "a"), os.path.join(base, "b")
    sh("printf 'L1\\nL2\\nL3\\n' > board.kicad_pcb && git add . && git commit -qm init && git push -q -u origin main", a)
    sh("git pull -q origin main && git branch -q -u origin/main", b)
    return base, a, b

def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, encoding="utf-8", errors="replace").stdout.strip()
