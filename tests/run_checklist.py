"""Run every test suite and print tests/kicad/CHECKLIST.md with the actual result of each test.

  python3 tests/run_checklist.py [--kicad] [--win-cmd "<prefix>"] [--python python3]

--kicad    also run the real-KiCad suite (needs KiCad pcbnew + Xvfb; ~10 min)
--win-cmd  command prefix that runs a WINDOWS python on test_windows_flows.py,
           e.g. under Wine; without it the flows run with the local python
Needs xvfb-run + wxPython. A test that could not run is reported as SKIP, never PASS."""
import os, re, sys, glob, subprocess, shutil, argparse, tempfile, ast
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser(); ap.add_argument("--kicad", action="store_true")
ap.add_argument("--win-cmd", default=""); ap.add_argument("--python", default=sys.executable)
args = ap.parse_args()
R = {}          # test id -> "PASS" / "FAIL ..." / "SKIP ..."
def xrun(cmd, env=None, timeout=3000):
    e = dict(os.environ)
    # Python started under the C locale coerces itself (PEP 538) by putting
    # LC_CTYPE=C.UTF-8 into os.environ; inherited, that would override the
    # LANG=zh_TW... we give child processes (Windows python then runs as cp1252).
    for k in ("LC_ALL", "LC_CTYPE"):
        e.pop(k, None)
    e.update(env or {})
    return subprocess.run(cmd, cwd=ROOT, env=e, capture_output=True, timeout=timeout, encoding="utf-8", errors="replace", shell=isinstance(cmd, str))
def parse(out, prefix):
    n = 0
    for m in re.finditer(r"^([BEW]\d+)_\S+\s+(PASS|FAIL.*|CRASH.*)$", out, re.M):
        R["%s:%s" % (prefix, m.group(1))] = m.group(2).strip(); n += 1
    return n

print("running unit suite ...", flush=True)
out = xrun(["xvfb-run", "-a", args.python, "tests/test_bugs.py"]).stdout
parse(out, "unit")
if os.path.exists("/usr/share/locale/zh_TW/LC_MESSAGES/git.mo") and "zh_TW.utf8" in xrun("locale -a").stdout:
    print("running unit suite with zh_TW git ...", flush=True)
    o = xrun(["xvfb-run", "-a", args.python, "tests/test_bugs.py"], {"LANG": "zh_TW.UTF-8", "LANGUAGE": "zh_TW"}).stdout
    res = re.findall(r"^[BEW]\d+_\S+\s+(PASS|FAIL.*|CRASH.*)$", o, re.M)
    R["unit-zh:ALL"] = ("PASS" if res and all(r == "PASS" for r in res) else "FAIL") + " (%d/%d)" % (res.count("PASS"), len(res))
else:
    R["unit-zh:ALL"] = "SKIP (no zh_TW git translation / locale installed)"

print("running ANSI code page test ...", flush=True)
if "zh_tw.big5" in xrun("locale -a").stdout.lower():
    f = tempfile.mktemp()
    xrun(["xvfb-run", "-a", args.python, "tests/test_ansi_codepage.py"], {"LANG": "zh_TW.BIG5", "PYTHONUTF8": "0", "PPS_OUT": f})
    t = open(f, encoding="utf-8").read() if os.path.exists(f) else ""
    R["ansi"] = "PASS" if re.search(r"RESULT\s+PASS", t) else "FAIL " + t[-200:]
else:
    R["ansi"] = "SKIP (locale zh_TW.BIG5 missing: localedef -i zh_TW -f BIG5 zh_TW.BIG5)"

print("running Windows flow test ...", flush=True)
f = tempfile.mktemp(dir=HERE, suffix=".txt")
if args.win_cmd:
    winf = "Z:" + f.replace("/", "\\")
    o = xrun(args.win_cmd + ' "%s" 2>&1 | cat' % ("Z:" + os.path.join(HERE, "test_windows_flows.py").replace("/", "\\")), {"PPS_OUT": winf})
else:
    o = xrun(["xvfb-run", "-a", args.python, "tests/test_windows_flows.py"], {"PPS_OUT": f})
t = open(f, encoding="utf-8").read() if os.path.exists(f) else ""
if os.path.exists(f): os.remove(f)
parse(t, "win")
plat = re.search(r"^platform\s+(\S+)", t, re.M); cp = re.search(r"^ansi code page\s+(\S+)", t, re.M)
wins = [v for k, v in R.items() if k.startswith("win:")]
R["win:ALL"] = ("PASS" if wins and all(v == "PASS" for v in wins) else "FAIL") + " (%d/%d on %s, %s)" % (
    wins.count("PASS"), len(wins), plat.group(1) if plat else "?", cp.group(1) if cp else "?")
if plat and plat.group(1) != "Windows":
    R["win:ALL"] = "SKIP (ran on %s, not a Windows python; pass --win-cmd)" % plat.group(1)

if args.kicad and shutil.which("pcbnew"):
    print("running real-KiCad suite (~10 min) ...", flush=True)
    o = xrun(["tests/kicad/run_all.sh"], {"PYTHON": args.python, "WORK": tempfile.mkdtemp(prefix="pps_kicad_")}, timeout=7200).stdout
    for name, verdict in re.findall(r"^===== (.+?)\n\s+-> (PASS|FAIL.*)$", o, re.M):
        R["kicad:" + name.replace("update: KiCad restart", "update_restart")] = verdict.strip()
else:
    R["kicad:*"] = "SKIP (pass --kicad on a machine with KiCad pcbnew)"

print("running static checks ...", flush=True)
problems = []
src = open(os.path.join(ROOT, "rtnexen_git_tools", "i18n.py"), encoding="utf-8").read()
node = next(n for n in ast.parse(src).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "STRINGS")
strings = ast.literal_eval(ast.unparse(node.value).replace("LANG_ZH", "'zh'").replace("LANG_EN", "'en'"))
ph = lambda s: set(re.findall(r"(?<!\{)\{(\w+)\}(?!\})", s))
for k, v in strings.items():
    if ph(v.get("zh", "")) != ph(v.get("en", "")): problems.append("%s: zh/en placeholders differ" % k)
for py in glob.glob(os.path.join(ROOT, "rtnexen_git_tools", "*.py")):
    tree = ast.parse(open(py, encoding="utf-8").read())
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("t", "t_en") and n.args and isinstance(n.args[0], ast.Constant):
            k = n.args[0].value
            if k not in strings: problems.append("%s:%d unknown key %s" % (os.path.basename(py), n.lineno, k)); continue
            if {kw.arg for kw in n.keywords} != ph(strings[k]["en"]): problems.append("%s:%d t(%r) args mismatch" % (os.path.basename(py), n.lineno, k))
pf = None
for py in (args.python, sys.executable, "python3"):
    r = xrun([py, "-m", "pyflakes", "rtnexen_git_tools"])
    if r.returncode in (0, 1) and "No module named" not in r.stderr:
        pf = r; break
if pf is not None:
    problems += [l for l in pf.stdout.splitlines() if "undefined name" in l or "syntax" in l.lower()]
    pf_note = ""
else:
    pf_note = " (pyflakes not installed: undefined-name scan skipped)"
R["static"] = ("PASS" + pf_note) if not problems else "FAIL " + "; ".join(problems[:5])

# ── print the checklist with results ──
rows = [l for l in open(os.path.join(HERE, "kicad", "CHECKLIST.md"), encoding="utf-8") if re.match(r"\|\s*[A-Z]\d+\s*\|", l)]
total = {"PASS": 0, "FAIL": 0, "SKIP": 0}
print("\n%-4s %-70s %s" % ("ID", "Flow", "Result"))
for l in rows:
    cid, flow, tests = [c.strip() for c in l.strip().strip("|").split("|")]
    res = []
    for tid in tests.split():
        v = R.get(tid) or (R.get("kicad:*") if tid.startswith("kicad:") else None) or "SKIP (not run)"
        res.append((tid, v))
    verdicts = [v.split()[0] for _, v in res]
    row = "FAIL" if "FAIL" in verdicts or "CRASH" in verdicts else ("PASS" if all(x == "PASS" for x in verdicts) else "PARTIAL" if "PASS" in verdicts else "SKIP")
    total["PASS" if row == "PASS" else "FAIL" if row == "FAIL" else "SKIP"] += 1
    print("%-4s %-70s %s" % (cid, flow[:70], row))
    for tid, v in res:
        print("       %-34s %s" % (tid, v[:110]))
print("\nchecklist rows: %(PASS)d PASS, %(FAIL)d FAIL, %(SKIP)d not fully run" % total)
sys.exit(1 if total["FAIL"] else 0)
