# PPS Tool tests

Two layers, both drive the real wxPython dialogs (no mocks of the plugin's own code):

| Suite | What it runs | Needs |
|---|---|---|
| `test_bugs.py` | 30 scenarios against real git repos (bare remote + two clones); `pcbnew` is stubbed | Python 3 + wxPython, git, Xvfb |
| `kicad/run_all.sh` | Starts the **real KiCad pcbnew editor** with the plugin installed and clicks through every user flow from `GitMainAction.Run()` (Push / Pull / Status / Settings / Batch / Auto-update + restart) | KiCad 7 (Linux), Xvfb |

```bash
xvfb-run -a python3 tests/test_bugs.py
```

```bash
tests/kicad/run_all.sh
```

Each KiCad scenario checks its own expected result and prints PASS / FAIL (`VERBOSE=1` shows details).

`test_ansi_codepage.py` runs the pull / status / push flows with Chinese commit messages while Python's
locale encoding is a legacy ANSI code page (as inside KiCad on Traditional-Chinese Windows):

```bash
LANG=zh_TW.BIG5 PYTHONUTF8=0 xvfb-run -a python3 tests/test_ansi_codepage.py
```

`test_windows_flows.py` is a portable flow test (no shell syntax) for a **Windows** Python with a
zh-TW locale: pull / status / push with Chinese messages and file names, auto-merge, conflict →
Overwrite Local, rejected push → Skip, Pull & Push rollback, restore to a commit, untracking, missing git, GUI.
Run it on Windows with any Python that has wxPython and git on PATH:

```bash
python tests/test_windows_flows.py
```

(Verified with Windows Python 3.11.10 + wxPython 4.2.2 + Git for Windows 2.47.1 under Wine with
`LANG=zh_TW.UTF-8`, i.e. ANSI code page cp950: 11/11 on v3.5.0, 1/11 on v3.4.2.)

Run `test_bugs.py` once more with a translated git (e.g. `LANG=zh_TW.UTF-8 LANGUAGE=zh_TW`, requires git's
zh_TW `.mo` file and the locale) to check the localized-git handling.

`tests/kicad/CHECKLIST.md` maps every user-reachable flow to the test that covers it.
To compare against an older version: `tests/kicad/run_all.sh /path/to/old/rtnexen_git_tools`.
