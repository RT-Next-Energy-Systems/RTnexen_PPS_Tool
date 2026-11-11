"""Run the plugin's git flows with Chinese commit messages / file names while
Python's locale encoding is a legacy ANSI code page (BIG5 here; cp950 = the
Traditional-Chinese Windows code page), as inside KiCad on zh-TW Windows.
Run:  LANG=zh_TW.BIG5 PYTHONUTF8=0 xvfb-run -a python3 tests/test_ansi_codepage.py
(needs the zh_TW.BIG5 locale:  localedef -i zh_TW -f BIG5 zh_TW.BIG5)"""
import os, sys, locale, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import *
from rtnexen_git_tools import status_dialog as sd, push_dialog as pd, pull_dialog as pl
res = {"python locale encoding": locale.getpreferredencoding(False)}
base, a, b = mkrepos()
open(os.path.join(b, "msg.txt"), "w", encoding="utf-8").write("批次更新 2026-11-11")   # teammate's commit, UTF-8 like git expects
sh("printf x > sch.kicad_sch && git add sch.kicad_sch && git commit -q -F msg.txt && git push -q", b)
for name, fn in [("pull (teammate's Chinese commit)", lambda: run_worker(pl._pull_one, log, a)),
                 ("status (Chinese commit in log)",   lambda: sd._status_fn(log, a, "P")),
                 ("push (Chinese file + message)",    lambda: (open(os.path.join(a, "佈局.kicad_pcb"), "w").write("y"), run_worker(pd._push_one, log, a, "更新原理圖"))[1])]:
    try:
        fn(); res[name] = "OK"
    except Exception as e:
        res[name] = "CRASH: %s: %s" % (type(e).__name__, str(e)[:90])
        res[name + " where"] = traceback.extract_tb(e.__traceback__)[-1].filename.split("/")[-1] + ":" + str(traceback.extract_tb(e.__traceback__)[-1].lineno)
remote = git(os.path.join(base, "remote.git"), "log", "--format=%s", "main")
res["status shows teammate's message"] = any("批次更新 2026-11-11" in l for l in LOG)
res["pushed message stored as UTF-8"] = remote.splitlines()[:1] == ["更新原理圖"]
ok = all(v in ("OK", True) for k, v in res.items() if k != "python locale encoding")
res["RESULT"] = "PASS" if ok else "FAIL"
out = os.environ.get("PPS_OUT")
lines = [f"{k:38s} {v}" for k, v in res.items()] + ["remote log: %s" % remote.splitlines()]
if out:
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
else:
    sys.stdout.buffer.write(("\n".join(lines) + "\n").encode("utf-8"))
