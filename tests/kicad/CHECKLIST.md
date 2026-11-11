# PPS Tool — every user-reachable flow and the test that covers it
(k_* = real KiCad pcbnew via tests/kicad/run_all.sh; B*/E* = tests/test_bugs.py)
| ID | Flow (entry: GitMainAction.Run inside real pcbnew) | Covered by |
|----|----|----|
| P1 | Push normal (commit + push) | k_push_basic |
| P2 | Push: nothing to commit, unpushed commits | test_bugs B18 |
| P3 | Push rejected → Pull & Push (clean / conflict rollback) | k_push_nff, B05 |
| P4 | Push rejected → Force Push | k_push_nff, B23 |
| P5 | Push overwrite mode (new) | k_overwrite |
| P6 | Push overwrite blocked by unsaved schematic | k_overwrite_block |
| P7 | Push draft: cancel→save draft→reopen→clear | k_draft, B24 |
| P8 | Push after Pull (stale board) | k_stale |
| P9 | Push ALL targets (project + library) | k_settings |
| L1 | Pull fast-forward | k_stale |
| L2 | Pull diverged (merge) | k_pull_conflict / B01 |
| L3 | Pull conflict → Overwrite Local / Keep Local | k_pull_conflict |
| L4 | Pull with uncommitted changes → Overwrite / Keep | k_pull_dirty |
| S1 | Status (tabs, colors, back to menu) | k_status |
| T1 | Settings: Remote1 name/url, scope switch global↔project, save | k_settings |
| T2 | Settings: export / import | k_settings, E06 |
| T3 | Settings: batch push / batch pull | k_batch |
| T4 | Settings: check update → auto update → restart | run_all.sh "update" (k_update + k_loadcheck) |
| T6 | Update dialog: skip version / open page | E07 |
| T5 | Settings: unsaved-changes prompt on Back | k_settings |
| N1 | Board not in a git repo → warning | k_nogit |
| G1 | git messages localized (zh_TW) | test_bugs (zh run) |
