"""Portable end-to-end flows (no shell syntax) — meant for a Windows Python
(e.g. KiCad's bundled one, or Windows Python + Git for Windows under Wine)
with a zh-TW system locale (ANSI code page cp950). Also runs on Linux/macOS.
Run:  python tests/test_windows_flows.py        (needs wxPython + git on PATH)
Results go to stdout as UTF-8, or to the file named by PPS_OUT."""
import os, sys, locale, platform, subprocess, tempfile, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import *                      # real wx, stub pcbnew, scripted dialogs, isolated HOME
import wx
from rtnexen_git_tools import common, pull_dialog as pl, push_dialog as pd, status_dialog as sd

YES, NO = wx.ID_YES, wx.ID_NO
def g(cwd, *args, inp=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, input=inp, encoding="utf-8", errors="replace")
    return r.stdout.strip()
def write(p, s): open(p, "w", encoding="utf-8").write(s)
def commit_utf8(cwd, msg):
    write(os.path.join(cwd, ".msg"), msg); g(cwd, "commit", "-q", "-F", ".msg"); os.remove(os.path.join(cwd, ".msg"))
def repos():
    base = tempfile.mkdtemp(prefix="ppswin_")
    rem, a, b = (os.path.join(base, n) for n in ("remote.git", "a", "b"))
    g(base, "init", "-q", "--bare", "-b", "main", rem)
    for c in (a, b):
        g(base, "clone", "-q", rem, c)
        for k, v in (("user.email", "t@t"), ("user.name", "T"), ("core.autocrlf", "false")): g(c, "config", k, v)
        g(c, "checkout", "-q", "-b", "main")
    write(os.path.join(a, "board.kicad_pcb"), "L1\nL2\nL3\n")
    pd._ensure_gitignore(lambda m: None, a)
    g(a, "add", "-A"); commit_utf8(a, "init"); g(a, "push", "-q", "-u", "origin", "main")
    g(b, "pull", "-q", "origin", "main"); g(b, "branch", "-q", "-u", "origin/main")
    return rem, a, b
def team(b, text, msg):
    write(os.path.join(b, "board.kicad_pcb"), "L1\n%s\nL3\n" % text); g(b, "add", "-A"); commit_utf8(b, msg); g(b, "push", "-q")

RES = {"platform": platform.system(), "python": sys.version.split()[0], "ansi code page": locale.getpreferredencoding(False),
       "git": g(".", "--version")}
CASES = {}
def case(f):
    LOG.clear(); SHOWN.clear(); ANSWERS.clear()
    try:
        ok = f(); CASES[f.__name__] = "PASS" if ok is not False else "FAIL"
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)[-1]
        CASES[f.__name__] = "CRASH %s: %s (%s:%s)" % (type(e).__name__, str(e)[:80], os.path.basename(tb.filename), tb.lineno)
    return f

@case
def W1_pull_teammate_chinese_commit_and_file():
    rem, a, b = repos()
    write(os.path.join(b, "原理圖.kicad_sch"), "x"); g(b, "add", "-A"); commit_utf8(b, "批次更新 修正 DRC"); g(b, "push", "-q")
    return bool(run_worker(pl._pull_one, log, a)) and os.path.exists(os.path.join(a, "原理圖.kicad_sch"))

@case
def W2_status_with_chinese_history():
    rem, a, b = repos()
    write(os.path.join(a, "x.txt"), "1"); g(a, "add", "-A"); commit_utf8(a, "更新電路圖"); write(os.path.join(a, "佈局.kicad_pcb"), "y")
    kind = sd._status_fn(log, a, "專案")
    return kind == "dirty" and any("更新電路圖" in l for l in LOG) and any("佈局.kicad_pcb" in l for l in LOG)

@case
def W3_push_chinese_message_and_file_stored_utf8():
    rem, a, b = repos()
    write(os.path.join(a, "新增元件.kicad_sym"), "z")
    run_worker(pd._push_one, log, a, "新增元件 U1")
    return g(rem, "log", "-1", "--format=%s", "main") == "新增元件 U1" and "新增元件.kicad_sym" in g(rem, "-c", "core.quotepath=false", "ls-tree", "--name-only", "main")

@case
def W4_pull_diverged_auto_merge():
    rem, a, b = repos(); team(b, "TEAM", "隊友修改")
    write(os.path.join(a, "other.txt"), "m"); g(a, "add", "-A"); commit_utf8(a, "mine")
    return bool(run_worker(pl._pull_one, log, a)) and "TEAM" in open(os.path.join(a, "board.kicad_pcb"), encoding="utf-8").read() and not SHOWN

@case
def W5_pull_conflict_overwrite_local():
    rem, a, b = repos(); team(b, "TEAM", "隊友修改")
    write(os.path.join(a, "board.kicad_pcb"), "L1\nMINE\nL3\n"); g(a, "add", "-A"); commit_utf8(a, "mine")
    ANSWERS[:] = [YES]
    ok = run_worker(pl._pull_one, log, a)
    return bool(ok) and bool(SHOWN) and "TEAM" in open(os.path.join(a, "board.kicad_pcb"), encoding="utf-8").read() and g(a, "status", "--porcelain") == ""

@case
def W6_push_rejected_force_push():
    rem, a, b = repos(); team(b, "TEAM", "隊友修改")
    write(os.path.join(a, "n.txt"), "n"); ANSWERS[:] = [NO]
    run_worker(pd._push_one, log, a, "強制覆蓋")
    return g(rem, "log", "-1", "--format=%s", "main") == "強制覆蓋"

@case
def W7_push_rejected_pull_and_push_conflict_rolls_back():
    rem, a, b = repos(); team(b, "TEAM", "隊友修改")
    write(os.path.join(a, "board.kicad_pcb"), "L1\nMINE\nL3\n"); ANSWERS[:] = [YES]
    run_worker(pd._push_one, log, a, "會衝突")
    return not common._rebase_in_progress(a) and "<<<<<<<" not in open(os.path.join(a, "board.kicad_pcb"), encoding="utf-8").read()

@case
def W8_overwrite_mode_push():
    rem, a, b = repos(); team(b, "TEAM", "隊友修改")
    write(os.path.join(a, "n.txt"), "n")
    run_worker(pd._push_one, log, a, "覆蓋遠端", True)
    return g(rem, "log", "--format=%s", "main").splitlines() == ["覆蓋遠端", "init"]

@case
def W9_untrack_ignored_chinese_file():
    rem, a, b = repos()
    write(os.path.join(a, "備份.bak"), "x"); g(a, "add", "-f", "備份.bak"); commit_utf8(a, "bak")
    common.untrack_ignored_files(a)
    return g(a, "ls-files", "--", "備份.bak") == ""

@case
def W10_git_missing_no_crash():
    old = os.environ["PATH"]; os.environ["PATH"] = ""
    try:
        return common._run(["git", "status"], ".").returncode != 0
    finally:
        os.environ["PATH"] = old

@case
def W11_gui_push_dialog_overwrite_toggle():
    from rtnexen_git_tools.push_dialog import PushDialog
    rem, a, b = repos()
    d = PushDialog(a)
    for _ in range(30): app.Yield(True)
    d.overwrite_chk.SetValue(True); d._on_overwrite_toggle(None)
    ok = d.GetOverwrite() and d.overwrite_hint.IsShown()
    d.Destroy(); return ok

RES.update(CASES)
RES["RESULT"] = "%d/%d PASS" % (sum(v == "PASS" for v in CASES.values()), len(CASES))
text = "\n".join("%-48s %s" % kv for kv in RES.items()) + "\n"
if os.environ.get("PPS_OUT"):
    open(os.environ["PPS_OUT"], "w", encoding="utf-8").write(text)
else:
    sys.stdout.buffer.write(text.encode("utf-8"))
