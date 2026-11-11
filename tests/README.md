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

Run `test_bugs.py` once more with a translated git (e.g. `LANG=zh_TW.UTF-8 LANGUAGE=zh_TW`, requires git's
zh_TW `.mo` file and the locale) to check the localized-git handling.

`tests/kicad/CHECKLIST.md` maps every user-reachable flow to the test that covers it.
To compare against an older version: `tests/kicad/run_all.sh /path/to/old/rtnexen_git_tools`.
