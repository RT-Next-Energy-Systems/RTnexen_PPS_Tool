"""usage: mkproj.py <dir> ; creates remote.git, a/ (opened in KiCad), b/ (teammate). Board text ORIGINAL."""
import sys, os, subprocess, pcbnew
D = sys.argv[1]; os.makedirs(D, exist_ok=True)
def sh(c, cwd=D): subprocess.run(c, cwd=cwd, shell=True, check=True, capture_output=True)
def board_set(path, text):
    b = pcbnew.LoadBoard(path) if os.path.exists(path) else pcbnew.BOARD()
    texts = [d for d in b.GetDrawings() if isinstance(d, pcbnew.PCB_TEXT)]
    if texts: texts[0].SetText(text)
    else:
        t = pcbnew.PCB_TEXT(b); t.SetText(text); b.Add(t)
    pcbnew.SaveBoard(path, b)
sh("git init -q --bare -b main remote.git && git clone -q remote.git a && git clone -q remote.git b")
for c in "ab": sh("git config user.email t@t && git config user.name T && git checkout -q -b main", os.path.join(D, c))
A, B = os.path.join(D, "a"), os.path.join(D, "b")
board_set(os.path.join(A, "board.kicad_pcb"), "ORIGINAL")
sh("printf '__pycache__/\\n*.bak\\n-backups/\\n_autosave-*\\n*.lck\\nfp-info-cache\\n.history/\\n*.pyc\\n.DS_Store\\nThumbs.db\\n*-bak.*\\n*.kicad_pcb-bak\\n*.kicad_sch-bak\\n*.000\\n' > .gitignore && git add -A && git commit -qm init && git push -q -u origin main", A)
sh("git pull -q origin main && git branch -q -u origin/main", B)
opts = sys.argv[2:]
if "teammate" in opts or "conflict" in opts:
    board_set(os.path.join(B, "board.kicad_pcb"), "TEAM")
    sh("git commit -qam team-change && git push -q", B)
if "conflict" in opts:      # A also changed the same text and committed (not pushed)
    board_set(os.path.join(A, "board.kicad_pcb"), "MINE")
    sh("git commit -qam mine-change", A)
if "otherfile" in opts:     # A committed a different file (diverged, no conflict)
    sh("echo mine > other.txt && git add other.txt && git commit -qm mine-other", A)
if "dirty" in opts:         # A has an uncommitted edit of the board
    board_set(os.path.join(A, "board.kicad_pcb"), "DIRTY")
if "lib" in opts:
    sh("git init -q --bare -b main lib.git && git clone -q lib.git lib")
    L = os.path.join(D, "lib")
    sh("git config user.email t@t && git config user.name T && git checkout -q -b main && echo sym > my.kicad_sym && git add . && git commit -qm lib-init && git push -q -u origin main", L)
if "nogit" in opts:
    import shutil; shutil.rmtree(os.path.join(A, ".git"))
