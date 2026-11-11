"""Bug-reproduction + regression tests for the PPS Tool (no KiCad needed).
Run: xvfb-run -a python3 tests/test_bugs.py   (needs wxPython; see tests/README.md)
Each B* test asserts the CORRECT behaviour and failed before its fix."""
import os, sys, traceback, subprocess
from harness import *
import wx
from rtnexen_git_tools import pull_dialog as pl, push_dialog as pd, status_dialog as sd, batch_dialog as bd, common, update_check as uc
YES, NO, CANCEL = wx.ID_YES, wx.ID_NO, wx.ID_CANCEL
RESULTS = {}
def case(fn):
    if os.environ.get("ONLY") and not fn.__name__.startswith(tuple(os.environ["ONLY"].split(","))): return fn
    LOG.clear(); SHOWN.clear(); ANSWERS.clear(); SAVED.clear()
    try:
        fn(); RESULTS[fn.__name__] = "PASS"
    except Exception as e:
        RESULTS[fn.__name__] = "FAIL: " + (str(e).splitlines() or [repr(e)])[0][:150]
        if os.environ.get("V"): traceback.print_exc(); print("\n".join(LOG))
    return fn

def diverge(a, b, conflict):
    sh("printf 'L1\\nTEAM\\nL3\\n' > board.kicad_pcb && git commit -qam team && git push -q", b)
    if conflict: sh("printf 'L1\\nMINE\\nL3\\n' > board.kicad_pcb && git commit -qam mine", a)
    else: sh("echo x > other.txt && git add . && git commit -qm mine", a)

@case
def B01_pull_divergent_no_conflict_merges():
    base, a, b = mkrepos(); diverge(a, b, conflict=False)
    ok = run_worker(pl._pull_one, log, a)
    assert ok, "pull failed: " + LOG[-1]
    assert "TEAM" in open(os.path.join(a, "board.kicad_pcb")).read()
    assert os.path.exists(os.path.join(a, "other.txt"))

@case
def B02_pull_conflict_overwrite_local_takes_remote():
    base, a, b = mkrepos(); diverge(a, b, conflict=True)
    ANSWERS[:] = [YES]   # Overwrite Local
    ok = run_worker(pl._pull_one, log, a)
    assert SHOWN, "no conflict dialog shown; log: " + LOG[-1]
    assert ok, "overwrite failed: " + LOG[-1]
    assert "TEAM" in open(os.path.join(a, "board.kicad_pcb")).read()
    assert git(a, "status", "--porcelain") == ""

@case
def B03_pull_uncommitted_filelist_not_truncated():
    base, a, b = mkrepos()
    sh("echo z >> board.kicad_pcb", a)
    ANSWERS[:] = [NO]
    run_worker(pl._pull_one, log, a)
    assert "board.kicad_pcb" in SHOWN[0][1], SHOWN[0][1]

@case
def B04_pull_overwrite_local_discards_staged_changes():
    base, a, b = mkrepos()
    sh("printf 'L1\\nTEAM\\nL3\\n' > board.kicad_pcb && git commit -qam team && git push -q", b)
    sh("printf 'L1\\nLOCAL\\nL3\\n' > board.kicad_pcb && git add board.kicad_pcb", a)  # staged
    ANSWERS[:] = [YES]
    ok = run_worker(pl._pull_one, log, a)
    assert ok, "overwrite failed: " + LOG[-1]
    assert "TEAM" in open(os.path.join(a, "board.kicad_pcb")).read()

@case
def B05_push_pull_and_push_conflict_does_not_leave_rebase():
    base, a, b = mkrepos(); diverge(a, b, conflict=False)
    sh("printf 'L1\\nMINE\\nL3\\n' > board.kicad_pcb", a)  # will conflict on rebase
    ANSWERS[:] = [YES]   # Pull & Push
    run_worker(pd._push_one, log, a, "msg")
    assert not common._rebase_in_progress(a), "repo left mid-rebase"
    assert "<<<<<<<" not in open(os.path.join(a, "board.kicad_pcb")).read(), "conflict markers left in board file"

@case
def B06_batch_push_conflict_does_not_leave_rebase():
    base, a, b = mkrepos(); diverge(a, b, conflict=False)
    sh("printf 'L1\\nMINE\\nL3\\n' > board.kicad_pcb", a)
    ANSWERS[:] = [YES]
    run_worker(bd._batch_push_one, log, a, "msg")
    assert not common._rebase_in_progress(a), "repo left mid-rebase"

@case
def B07_status_ahead_substring_false_positive():
    base, a, b = mkrepos()
    sh("git checkout -q -b ahead-fix && git push -q -u origin ahead-fix", a)
    kind = sd._status_fn(log, a, "P")
    assert kind == "clean", kind

@case
def B08_run_utf8_output_independent_of_locale():
    base, a, b = mkrepos()
    sh("echo 1 > f && git add . && git commit -qm '批次更新 測試'", a)
    code = ("import sys,types; sys.path.insert(0,%r); sys.dont_write_bytecode=True;"
            "p=types.ModuleType('pcbnew'); p.ActionPlugin=type('A',(),{'register':lambda s:None}); sys.modules['pcbnew']=p;"
            "from rtnexen_git_tools import common;"
            "r=common._run(['git','log','--format=%%s','-1'],%r); sys.stdout.buffer.write(r.stdout.encode(\"utf-8\"))" % (ROOT, a))
    env = dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0")
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, (r.stderr.strip().splitlines() or ["?"])[-1]
    assert "批次更新" in r.stdout, r.stdout

@case
def B09_run_git_missing_does_not_raise():
    old = os.environ["PATH"]; os.environ["PATH"] = "/nonexistent"
    try:
        r = common._run(["git", "status"], "/tmp")
    finally:
        os.environ["PATH"] = old
    assert r.returncode != 0

@case
def B10_untrack_ignored_non_ascii_path():
    base, a, b = mkrepos()
    sh("echo x > '備份.bak' && git add . && git commit -qm bak && echo '*.bak' > .gitignore", a)
    common.untrack_ignored_files(a)
    assert git(a, "ls-files", "--", "備份.bak") == "", "ignored file still tracked"

@case
def B11_operation_dialog_finishes_on_exception():
    from rtnexen_git_tools.operation_dialog import OperationDialog
    def boom(log, path): raise RuntimeError("boom")
    dlg = OperationDialog("x", "/tmp", boom)
    wx.CallLater(1500, app.ExitMainLoop)
    app.MainLoop()
    enabled = dlg.close_btn.IsEnabled(); txt = dlg.log.GetValue()
    dlg.Destroy()
    assert enabled, "Close button never enabled after worker exception"
    assert "boom" in txt, "error not shown in log"

@case
def B12_settings_name1_saved_on_git_init():
    from rtnexen_git_tools.settings_dialog import SettingsDialog
    import tempfile
    proj = tempfile.mkdtemp()
    dlg = SettingsDialog(proj)
    wx.CallLater(300, app.ExitMainLoop); app.MainLoop()
    dlg.name1_ctrl.SetValue("MyProj"); dlg.url1_ctrl.SetValue("https://example.com/x.git")
    dlg.name2_ctrl.SetValue(""); dlg.path2_ctrl.SetValue(""); dlg.url2_ctrl.SetValue("")
    dlg._apply(None); dlg.Destroy()
    assert git(proj, "config", "--get", "rtnexen.remote1name") == "MyProj", "name lost"

@case
def B13_update_backup_not_inside_kicad_plugins_dir():
    import tempfile, zipfile, io
    plugins = tempfile.mkdtemp(); inst = os.path.join(plugins, "rtnexen_git_tools")
    os.makedirs(inst); open(os.path.join(inst, "__init__.py"), "w").write("#old")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z: z.writestr("Repo-v9/rtnexen_git_tools/__init__.py", "#new")
    class R:
        def __enter__(s): return s
        def __exit__(s, *a): pass
        def read(s): return buf.getvalue()
    orig = (uc.PLUGIN_DIR, uc.PLUGINS_PARENT, uc.urllib.request.urlopen)
    uc.PLUGIN_DIR, uc.PLUGINS_PARENT = inst, plugins
    uc.urllib.request.urlopen = lambda *a, **k: R()
    try:
        ok, info = uc.download_and_install_update("v9")
    finally:
        uc.PLUGIN_DIR, uc.PLUGINS_PARENT, uc.urllib.request.urlopen = orig
    assert ok, info
    assert open(os.path.join(inst, "__init__.py")).read() == "#new"
    pkgs = [d for d in os.listdir(plugins) if os.path.isfile(os.path.join(plugins, d, "__init__.py"))]
    assert pkgs == ["rtnexen_git_tools"], "extra plugin packages KiCad will try to load: %s" % pkgs

@case
def B14_push_after_pull_does_not_save_stale_board():
    import time
    base, a, b = mkrepos()
    BOARD["file"] = f = os.path.join(a, "board.kicad_pcb")
    sh("printf 'L1\\nTEAM\\nL3\\n' > board.kicad_pcb && git commit -qam team && git push -q", b)
    common.watch_open_board(lambda: run_worker(pl._pull_one, log, a))   # = run_pull
    assert common.save_open_board() == "stale"                           # = run_push save step
    assert "TEAM" in open(f).read(), "stale in-memory board overwrote pulled file"
    time.sleep(0.02); open(f, "a").write("saved from KiCad\n")         # user reloads, edits, Ctrl+S
    assert common.save_open_board() == "saved", "normal save not restored after user saved"
    BOARD["file"] = ""

@case
def B16_pull_divergent_no_conflict_merge_commit_ok_in_batch():
    base, a, b = mkrepos(); diverge(a, b, conflict=False)
    out, _ = run_worker(bd._batch_pull_one, log, a, None)
    assert out == "ok", out + " / " + LOG[-1]

@case
def B17_batch_pull_conflict_overwrite_takes_remote():
    base, a, b = mkrepos(); diverge(a, b, conflict=True)
    ANSWERS[:] = [YES, NO]
    out, _ = run_worker(bd._batch_pull_one, log, a, None)
    assert out == "ok", out + " / " + LOG[-1]
    assert "TEAM" in open(os.path.join(a, "board.kicad_pcb")).read()

@case
def E01_push_dialog_overwrite_checkbox_gui():
    from rtnexen_git_tools.push_dialog import PushDialog
    base, a, b = mkrepos()
    dlg = PushDialog(a)
    for _ in range(30): app.Yield(True)
    assert not dlg.GetOverwrite()
    assert not dlg.overwrite_hint.IsShown()
    dlg.overwrite_chk.SetValue(True)
    dlg._on_overwrite_toggle(None)
    shown, label, ov = dlg.overwrite_hint.IsShown(), dlg.ok_btn.GetLabel(), dlg.GetOverwrite()
    dlg.Destroy()
    assert ov and shown and label == "Overwrite Remote", (ov, shown, label)

def _run_push_e2e(a, overwrite, answers, messages=None, targets=None):
    from rtnexen_git_tools import git_runner as gr
    class FakePush:
        def __init__(s, p): pass
        def ShowModal(s): return wx.ID_OK
        def GetMessages(s): return messages or {"project": "e2e commit", "library": ""}
        def GetTargets(s): return targets or [{"name": "P", "path": a, "kind": "project"}]
        def GetOverwrite(s): return overwrite
        def Destroy(s): pass
    class FakeOp:
        def __init__(s, sub, path, fn): s.fn, s.path = fn, path
        def ShowModal(s): run_worker(s.fn, log, s.path); return wx.ID_OK
        def Destroy(s): pass
    orig = gr.PushDialog, gr.OperationDialog
    gr.PushDialog, gr.OperationDialog = FakePush, FakeOp
    ANSWERS[:] = answers
    try: gr.run_push(a)
    finally: gr.PushDialog, gr.OperationDialog = orig

@case
def E02_run_push_overwrite_end_to_end():
    base, a, b = mkrepos(); diverge(a, b, conflict=True)
    sh("echo new > note.txt", a)
    _run_push_e2e(a, True, [YES])          # confirm overwrite
    remote = os.path.join(base, "remote.git")
    assert git(remote, "log", "-1", "--format=%s", "main") == "e2e commit", "\n".join(LOG)
    assert "team" not in git(remote, "log", "--format=%s", "main")

@case
def E03_run_push_overwrite_blocked_by_unsaved_schematic():
    import time
    base, a, b = mkrepos()
    sh("echo s > top.kicad_sch && git add . && git commit -qm sch && git push -q", a)
    time.sleep(0.02); sh("echo unsaved > _autosave-top.kicad_sch", a)
    before = git(os.path.join(base, "remote.git"), "rev-parse", "main")
    _run_push_e2e(a, True, [YES])          # first YES = continue past the generic pre-dialog warning
    assert any("Cannot Overwrite" in c for c, m in SHOWN), SHOWN
    assert git(os.path.join(base, "remote.git"), "rev-parse", "main") == before, "remote changed"
    from rtnexen_git_tools.i18n import get_commit_draft
    assert get_commit_draft(a) == "e2e commit", "commit message not kept as draft"

@case
def E04_normal_push_and_pull_roundtrip():
    base, a, b = mkrepos()
    sh("echo hi > 中文檔名.txt", a)
    _run_push_e2e(a, False, [])
    assert run_worker(pl._pull_one, log, b), "\n".join(LOG)
    assert os.path.exists(os.path.join(b, "中文檔名.txt"))
    assert sd._status_fn(log, b, "B") == "clean"

@case
def B18_push_nothing_to_commit_still_pushes_unpushed_commits():
    base, a, b = mkrepos()
    pd._ensure_gitignore(log, a); sh("git add . && git commit -qm gi && git push -q", a)
    sh("echo 1 > f && git add . && git commit -qm local-only", a)   # committed, not pushed
    run_worker(pd._push_one, log, a, "msg")
    assert git(os.path.join(base, "remote.git"), "log", "-1", "--format=%s", "main") == "local-only", "\n".join(LOG)

@case
def B19_push_rejected_shows_nff_dialog():
    base, a, b = mkrepos(); diverge(a, b, conflict=False)
    ANSWERS[:] = [CANCEL]   # Skip
    run_worker(pd._push_one, log, a, "msg")
    assert SHOWN and "Non-Fast-Forward" in SHOWN[0][0], "NFF not recognised: " + "\n".join(LOG[-3:])

@case
def B20_chinese_commit_message_roundtrip():
    base, a, b = mkrepos()
    sh("echo 1 > 原理圖.kicad_sch", a)
    run_worker(pd._push_one, log, a, "更新原理圖 修正 DRC")
    assert git(os.path.join(base, "remote.git"), "log", "-1", "--format=%s", "main") == "更新原理圖 修正 DRC"
    LOG.clear(); sd._status_fn(log, a, "P")
    assert any("更新原理圖 修正 DRC" in l for l in LOG), LOG

@case
def B21_batch_scan_ignores_plain_subfolders_of_a_parent_repo():
    import tempfile
    root = tempfile.mkdtemp()
    sh("git init -q . && mkdir projA projB && git init -q projB", root)   # root is a repo; projA is NOT
    names = [r["name"] for r in bd.scan_batch_repos(root)]
    assert names == ["projB"], names

@case
def B22_push_dialog_autofill_not_reported_as_unsaved_draft():
    from rtnexen_git_tools.push_dialog import PushDialog
    base, a, b = mkrepos()
    sh("git checkout -q -b feature-x", a)
    dlg = PushDialog(a)
    import time
    for _ in range(100): app.Yield(True); time.sleep(0.005)
    val = dlg.msg_ctrls["project"].GetValue(); unsaved = dlg._has_unsaved_drafts()
    dlg.msg_ctrls["project"].SetValue("typed by user"); unsaved2 = dlg._has_unsaved_drafts()
    dlg.Destroy()
    assert val == "Update feature-x", val
    assert not unsaved, "auto-filled default message triggers the unsaved-draft prompt on Cancel"
    assert unsaved2

@case
def E05_empty_library_message_keeps_project_message():
    from rtnexen_git_tools.i18n import get_commit_draft
    base, a, b = mkrepos(); base2, lib, _ = mkrepos()
    _run_push_e2e(a, False, [], messages={"project": "my long project msg", "library": ""},
                  targets=[{"name": "P", "path": a, "kind": "project"}, {"name": "L", "path": lib, "kind": "library"}])
    assert any("cannot be empty" in m for c, m in SHOWN), SHOWN
    assert get_commit_draft(a) == "my long project msg", "typed project message was discarded"

@case
def B23_force_push_after_rejection_works():
    base, a, b = mkrepos(); diverge(a, b, conflict=False)
    ANSWERS[:] = [NO]    # Force Push
    run_worker(pd._push_one, log, a, "forced")
    assert git(os.path.join(base, "remote.git"), "log", "-1", "--format=%s", "main") == "forced", "\n".join(LOG[-4:])

@case
def B24_push_cancel_prompt_bound_to_own_button():
    from rtnexen_git_tools.push_dialog import PushDialog
    base, a, b = mkrepos()
    other = wx.Dialog(None); wx.Button(other, wx.ID_CANCEL, "Cancel")   # e.g. the main menu behind it
    d = PushDialog(a)
    def act():
        d.msg_ctrls["project"].SetValue("typed")
        ANSWERS[:] = [NO]    # "Save"
        btn = d.cancel_btn if getattr(d, "cancel_btn", None) else [c for c in d.panel.GetChildren() if isinstance(c, wx.Button) and c.GetId() == wx.ID_CANCEL][0]
        ev = wx.CommandEvent(wx.wxEVT_BUTTON, wx.ID_CANCEL); ev.SetEventObject(btn); btn.GetEventHandler().ProcessEvent(ev)
    wx.CallLater(300, act)
    d.ShowModal(); d.Destroy(); other.Destroy()
    from rtnexen_git_tools.i18n import get_commit_draft
    assert SHOWN, "no unsaved-draft prompt on Cancel"
    assert get_commit_draft(a) == "typed"

@case
def E06_settings_import_roundtrip():
    import json, tempfile
    from rtnexen_git_tools.settings_dialog import SettingsDialog
    base, a, b = mkrepos()
    f = os.path.join(tempfile.mkdtemp(), "exp.json")
    json.dump({"language": "en", "remote2_name": "LibX", "remote2_path": "/machine/specific", "remote2_url": "https://x/y.git"}, open(f, "w"))
    class FD:
        def __init__(s, *a, **k): pass
        def ShowModal(s): return wx.ID_OK
        def GetPath(s): return f
        def Destroy(s): pass
    orig = wx.FileDialog; wx.FileDialog = FD
    try:
        d = SettingsDialog(a); ANSWERS[:] = [YES]
        d._on_import_settings(None)
        for _ in range(50): app.Yield(True)
        d.Destroy()
    finally:
        wx.FileDialog = orig
    i18n._cache = None
    assert i18n.get_global_remote2() == ("LibX", ""), i18n.get_global_remote2()   # path is machine-specific -> dropped
    assert i18n.get_global_remote2_url() == "https://x/y.git"
    i18n.set_language("en")

@case
def E07_update_dialog_skip_and_open():
    import webbrowser
    opened = []; orig = webbrowser.open; webbrowser.open = lambda u: opened.append(u)
    try:
        d = uc.UpdateDialog("v9.9.9", "3.5.0", "readme")
        wx.CallLater(200, lambda: d._on_skip(None)); d.ShowModal(); d.Destroy()
        d = uc.UpdateDialog("v9.9.9", "3.5.0", "readme")
        wx.CallLater(200, lambda: d._on_update(None)); d.ShowModal(); d.Destroy()
    finally:
        webbrowser.open = orig
    assert i18n.get_skipped_version() == "v9.9.9"
    assert opened == [uc.REPO_URL]
    assert uc._parse_version("v3.10.0") > uc._parse_version("3.9.9") and uc._parse_version("v3.5.0") == (3, 5, 0)

@case
def B25_unsaved_detection_kicad10_user_dir_autosave():
    # KiCad 10: Preferences > Backups > "user directory" (kicad_common.json
    # auto_backup.location = 1) mirrors autosaves under
    # <settings>/autosave/<ProjectName>-<sha256(project file)[:12]>/ with NO "_autosave-" prefix.
    import json, hashlib, tempfile, time
    settings, proj = tempfile.mkdtemp(), tempfile.mkdtemp()
    json.dump({"auto_backup": {"location": 1}}, open(os.path.join(settings, "kicad_common.json"), "w"))
    pro = os.path.join(proj, "board.kicad_pro"); open(pro, "w").write("{}")
    os.makedirs(os.path.join(proj, "sub"))
    for f in ("top.kicad_sch", os.path.join("sub", "child.kicad_sch"), "board.kicad_pcb"):
        open(os.path.join(proj, f), "w").write("saved")
    root = os.path.join(settings, "autosave", "board-" + hashlib.sha256(pro.encode("utf-8")).hexdigest()[:12])
    time.sleep(0.05)
    os.makedirs(os.path.join(root, "sub"))
    open(os.path.join(root, "sub", "child.kicad_sch"), "w").write("UNSAVED EDIT")   # newer + different
    open(os.path.join(root, "board.kicad_pcb"), "w").write("saved")                  # newer but identical
    orig = getattr(pd, "_kicad_user_settings_dir", None)
    pd._kicad_user_settings_dir = lambda: settings
    try:
        found = pd.check_unsaved_design_files(proj)
    finally:
        if orig: pd._kicad_user_settings_dir = orig
    assert found == [os.path.join("sub", "child.kicad_sch")], found

@case
def B26_unsaved_detection_ignores_identical_autosave():
    # KiCad 10 itself treats a newer-but-byte-identical autosave (e.g. touched by a
    # cloud-sync client) as NOT unsaved; don't block the push for it.
    import tempfile, time
    proj = tempfile.mkdtemp()
    open(os.path.join(proj, "top.kicad_sch"), "w").write("same"); time.sleep(0.05)
    open(os.path.join(proj, "_autosave-top.kicad_sch"), "w").write("same")
    assert pd.check_unsaved_design_files(proj) == []

def _upd_fixture():
    """Installed plugin (with sub-folders) in a fake KiCad plugins dir + a fake release zip."""
    import tempfile, zipfile, io
    plugins = tempfile.mkdtemp(); inst = os.path.join(plugins, "rtnexen_git_tools")
    os.makedirs(os.path.join(inst, "icons")); os.makedirs(os.path.join(inst, "__pycache__"))
    for f, c in (("__init__.py", "#old"), ("a.py", "old"), ("icons/x.png", "oldpng"), ("__pycache__/a.pyc", "pyc")):
        open(os.path.join(inst, f), "w").write(c)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for f, c in (("__init__.py", "#new"), ("a.py", "new"), ("new_module.py", "new"), ("icons/x.png", "newpng")):
            z.writestr("R-9/rtnexen_git_tools/" + f, c)
    class Resp:
        def __enter__(s): return s
        def __exit__(s, *a): pass
        def read(s): return buf.getvalue()
    return plugins, inst, Resp

def _snapshot_tree(d):
    out = {}
    for root, _, files in os.walk(d):
        for f in files:
            out[os.path.relpath(os.path.join(root, f), d)] = open(os.path.join(root, f)).read()
    return out

def _run_update(plugins, inst, Resp, copytree_fail=None, replace_fail=None):
    """copytree_fail(src, dst) / replace_fail(src, dst) -> True to raise there."""
    import shutil as _sh
    real_ct, real_rp = _sh.copytree, os.replace
    def ct(src, dst, *a, **k):
        if copytree_fail and copytree_fail(str(src), str(dst)):
            os.makedirs(dst, exist_ok=True); open(os.path.join(dst, "partial"), "w").write("x")
            raise _sh.Error([(str(src) + "/f%d" % i, str(dst) + "/f%d" % i, "[Errno 28] No space left on device") for i in range(60)])
        return real_ct(src, dst, *a, **k)
    def rp(src, dst):
        if replace_fail and replace_fail(str(src), str(dst)):
            raise PermissionError(13, "The process cannot access the file because it is being used by another process")
        return real_rp(src, dst)
    saved = (uc.PLUGIN_DIR, uc.PLUGINS_PARENT, uc.urllib.request.urlopen)
    uc.PLUGIN_DIR, uc.PLUGINS_PARENT = inst, plugins
    uc.urllib.request.urlopen = lambda *a, **k: Resp()
    _sh.copytree, os.replace = ct, rp
    try:
        return uc.download_and_install_update("v9")
    finally:
        _sh.copytree, os.replace = real_ct, real_rp
        uc.PLUGIN_DIR, uc.PLUGINS_PARENT, uc.urllib.request.urlopen = saved

def _no_leftovers(plugins):
    import glob as _g
    left = [p for p in os.listdir(plugins) if p != "rtnexen_git_tools"]
    left += _g.glob(os.path.join(HOME, ".rtnexen_pps_tool", "update_staging", "*")) + \
            _g.glob(os.path.join(HOME, ".rtnexen_pps_tool", "update_staging", ".*"))
    return left

OLD_TREE = {"__init__.py": "#old", "a.py": "old", os.path.join("icons", "x.png"): "oldpng", os.path.join("__pycache__", "a.pyc"): "pyc"}

@case
def B27_update_fails_while_copying_new_version_plugin_untouched():
    plugins, inst, Resp = _upd_fixture()
    ok, msg = _run_update(plugins, inst, Resp, copytree_fail=lambda s, d: d.endswith("-new"))
    assert not ok and _snapshot_tree(inst) == OLD_TREE, _snapshot_tree(inst)
    assert _no_leftovers(plugins) == [], _no_leftovers(plugins)
    assert len(msg) < 600 and "59" in msg, "error not summarised: %d chars" % len(msg)
    assert "not changed" in msg

@case
def B28_update_locked_file_rename_fails_plugin_untouched():
    plugins, inst, Resp = _upd_fixture()
    ok, msg = _run_update(plugins, inst, Resp, replace_fail=lambda s, d: s == inst)
    assert not ok and _snapshot_tree(inst) == OLD_TREE and _no_leftovers(plugins) == []
    assert "not changed" in msg

@case
def B29_update_swap_fails_old_version_renamed_back():
    plugins, inst, Resp = _upd_fixture()
    ok, msg = _run_update(plugins, inst, Resp, replace_fail=lambda s, d: s.endswith("-new"))
    assert not ok and _snapshot_tree(inst) == OLD_TREE, _snapshot_tree(inst)
    assert _no_leftovers(plugins) == [], _no_leftovers(plugins)

@case
def B30_update_double_failure_tells_user_to_rename_backup():
    plugins, inst, Resp = _upd_fixture()
    ok, msg = _run_update(plugins, inst, Resp, replace_fail=lambda s, d: d == inst)
    assert not ok and "rtnexen_git_tools" in msg and "rename" in msg, msg
    import re as _re
    backup = _re.search(r"\n(/\S+backups\S+)\n", msg).group(1)
    assert _snapshot_tree(backup) == OLD_TREE, "backup named in the message is not the intact old version"

@case
def B31_update_success_and_retry_keep_every_backup():
    plugins, inst, Resp = _upd_fixture()
    ok1, b1 = _run_update(plugins, inst, Resp)
    ok2, b2 = _run_update(plugins, inst, Resp)
    assert ok1 and ok2 and b1 != b2 and os.path.isdir(b1) and os.path.isdir(b2), (b1, b2)
    assert _snapshot_tree(b1) == OLD_TREE, "first (only good) backup was overwritten"
    assert _snapshot_tree(inst) == {"__init__.py": "#new", "a.py": "new", "new_module.py": "new", os.path.join("icons", "x.png"): "newpng"}
    assert _no_leftovers(plugins) == [], _no_leftovers(plugins)

for k, v in RESULTS.items(): print(f"{k:55s} {v}")
