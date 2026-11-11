#!/bin/bash
# End-to-end tests inside the REAL KiCad pcbnew editor (KiCad 7, Linux, Xvfb).
# usage: tests/kicad/run_all.sh [plugin_pkg_dir] [scenario-regex]
#   plugin_pkg_dir defaults to this repo's rtnexen_git_tools (pass an older
#   checkout's folder to compare behaviour before/after a fix)
S=$(cd $(dirname $0); pwd); PKG=${1:-$S/../../rtnexen_git_tools}; F=${2:-.}
WORK=${WORK:-$(mktemp -d /tmp/pps_kicad_XXXX)}
run() {  # name scenario "mkproj opts" "env"
  local N=$1 SCN=$2 OPTS=$3 ENVS=$4
  echo "$N" | grep -qE "$F" || return 0
  local W=$WORK/$N; rm -rf $W; mkdir -p $W/home
  ${PYTHON:-python3} $S/mkproj.py $W/p $OPTS || { echo "$N: setup failed"; return; }
  printf '[user]\nemail=t@t\nname=T\n' > $W/home/.gitconfig
  env $ENVS $S/run_kicad.sh $PKG $W/home $W/p/a/board.kicad_pcb $S/$SCN > /dev/null
  echo "===== $N"; python3 $S/show.py $W/home/result.json | cut -c1-600
}
run push_basic      k_push_basic.py ""
run push_nff_pull   k_push_nff.py   "teammate"          "NFF_MODE=pull_push"
run push_nff_force  k_push_nff.py   "teammate"          "NFF_MODE=force"
run overwrite       k_overwrite.py  "teammate"
run overwrite_block k_overwrite.py  ""                  "OV_BLOCK=1"
run draft           k_draft.py      ""
run pull_conflict_overwrite k_pull.py "conflict"        "PULL_ANSWER=overwrite"
run pull_conflict_keep      k_pull.py "conflict"        "PULL_ANSWER=keep"
run pull_dirty_overwrite    k_pull.py "teammate dirty"  "PULL_ANSWER=overwrite"
run pull_dirty_keep         k_pull.py "teammate dirty"  "PULL_ANSWER=keep"
run status          k_status.py     "lib"
run nogit           k_nogit.py      "nogit"
run settings        k_settings.py   "lib"
run batch           k_batch.py      ""
run stale           k_stale.py      "teammate"
# auto-update from a local fake GitHub, then restart KiCad and read its plugin-loader report
if echo update | grep -qE "$F"; then
  SRV=$WORK/srv; mkdir -p $SRV; echo '{"tag_name":"v9.9.9"}' > $SRV/api.json; echo "# README" > $SRV/README.md
  (cd $S/../.. && git archive --format=zip --prefix=RTnexen_PPS_Tool-9.9.9/ HEAD -o $SRV/v9.9.9.zip)
  (cd $SRV && exec python3 -m http.server 8765 --bind 127.0.0.1 >/dev/null 2>&1) & SP=$!; sleep 1
  W=$WORK/update; rm -rf $W; mkdir -p $W/home; ${PYTHON:-python3} $S/mkproj.py $W/p; printf '[user]\nemail=t@t\nname=T\n' > $W/home/.gitconfig
  $S/run_kicad.sh $PKG $W/home $W/p/a/board.kicad_pcb $S/k_update.py >/dev/null
  echo "===== update"; python3 $S/show.py $W/home/result.json | cut -c1-300
  $S/run_kicad_keep.sh $W/home $W/p/a/board.kicad_pcb $S/k_loadcheck.py
  echo "===== update: KiCad restart"; python3 $S/show.py $W/home/result.json | grep -E "load_errors|rtnexen_modules"
  kill $SP
fi
