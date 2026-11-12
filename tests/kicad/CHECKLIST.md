# PPS Tool — every user-reachable flow and the tests that cover it

`python3 tests/run_checklist.py` runs every suite and prints this table with the actual result of each test.

Test ids: `kicad:<scenario>` = real KiCad pcbnew editor (tests/kicad/run_all.sh) ·
`unit:<id>` = tests/test_bugs.py · `unit-zh:ALL` = the whole unit suite with a zh_TW-translated git ·
`win:<id>` = tests/test_windows_flows.py (Windows Python + Git for Windows, cp950) ·
`ansi` = tests/test_ansi_codepage.py (BIG5 locale) · `static` = compile + i18n placeholder + undefined-name scan

| ID | Flow | Tests |
|----|------|-------|
| P1 | Push: commit + push | kicad:push_basic win:W3 unit:E04 |
| P2 | Push: nothing to commit, unpushed commits | unit:B18 |
| P3 | Push rejected → Pull & Push (incl. conflict rollback) | kicad:push_nff_pull unit:B05 unit:B06 unit:B19 win:W7 |
| P4 | Push rejected → Skip (Force Push was removed in v3.5.3; the dialog offers only Pull & Push / Skip) | kicad:push_nff_skip unit:B23 win:W6 |
| P5 | Settings → Restore to a commit: pick a commit, typed confirmation, overwrite local files, plain Push afterwards (new in v3.5.3) | unit:E01 unit:E08 unit:E09 unit:E10 unit:E11 win:W8 win:W11 |
| P7 | Push drafts: cancel → save → reopen → clear; autofill; empty message | kicad:draft unit:B22 unit:B24 unit:E05 |
| P8 | Push right after Pull / Pull & Push (stale board in editor) | kicad:stale unit:B14 unit:B32 |
| P9 | Push ALL / single targets (incl. Remote 2 named "ALL") | kicad:settings unit:B35 |
| L1 | Pull fast-forward (incl. Chinese commit / file names) | kicad:stale win:W1 unit:B20 |
| L2 | Pull diverged, no conflict → auto merge | kicad:pull_merge unit:B01 unit:B16 win:W4 |
| L3 | Pull conflict → Overwrite Local / Keep Local (batch "apply to all" per prompt kind) | kicad:pull_conflict_overwrite kicad:pull_conflict_keep unit:B02 unit:B17 unit:B33 win:W5 |
| L4 | Pull with uncommitted changes → Overwrite / Keep | kicad:pull_dirty_overwrite kicad:pull_dirty_keep unit:B03 unit:B04 |
| S1 | Status (fetch, ahead/behind, tabs, colours, back to menu) | kicad:status unit:B07 unit:B37 win:W2 |
| T1 | Settings: Remote 1/2 (git init, separate-repo check), scope switch, save | kicad:settings unit:B12 unit:B38 unit:B40 |
| T2 | Settings: export / import (keeps this PC's paths) | kicad:settings unit:E06 unit:B36 |
| T3 | Settings: batch push / batch pull | kicad:batch unit:B21 |
| T4 | Auto update: automatic popup / Settings → Check for Updates (skip honoured) → install → KiCad restart; failed install never damages the plugin | kicad:update_auto kicad:update_auto_restart kicad:update_manual kicad:update_manual_restart unit:B13 unit:B27 unit:B28 unit:B29 unit:B30 unit:B31 |
| T5 | Settings: unsaved-changes prompt on Back | kicad:settings |
| T6 | Update: automatic check, skip version, open page, version compare | unit:E07 unit:B39 |
| N1 | Board not in a git repo → warning | kicad:nogit |
| R1 | Robustness: UTF-8 output, missing git, worker exceptions, no close mid-operation, non-ASCII files, every dialog | unit:B08 unit:B09 unit:B10 unit:B11 unit:B34 win:W9 win:W10 win:W12 |
| G1 | git messages translated (zh_TW) | unit-zh:ALL |
| G2 | Python on a legacy ANSI code page (BIG5 ≈ zh-TW Windows cp950) | ansi |
| G3 | Static: compiles, i18n placeholders match call sites, no undefined names | static |
| G4 | Windows runtime (Windows Python 3.11 + wxPython + Git for Windows, cp950) | win:ALL |
