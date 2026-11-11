#!/bin/bash
# End-to-end tests inside the REAL KiCad pcbnew editor (KiCad 7, Linux, Xvfb).
# usage: tests/kicad/run_all.sh [plugin_pkg_dir] [scenario-regex]
#   plugin_pkg_dir defaults to this repo's rtnexen_git_tools (pass an older
#   checkout's folder to compare behaviour before/after a fix)
S=$(cd $(dirname $0); pwd); PKG=${1:-$S/../../rtnexen_git_tools}; F=${2:-.}
WORK=${WORK:-$(mktemp -d /tmp/pps_kicad_XXXX)}
PASSN=0; FAILN=0
verdict() { local V; V=$(python3 $S/check.py "$1" "$2"); echo "  -> $V"; case $V in PASS*) PASSN=$((PASSN+1));; *) FAILN=$((FAILN+1));; esac; }
run() {  # name scenario "mkproj opts" "env" "expectation over r"
  local N=$1 SCN=$2 OPTS=$3 ENVS=$4 EXP=$5
  echo "$N" | grep -qE "$F" || return 0
  local W=$WORK/$N; rm -rf $W; mkdir -p $W/home
  ${PYTHON:-python3} $S/mkproj.py $W/p $OPTS || { echo "$N: setup failed"; return; }
  printf '[user]\nemail=t@t\nname=T\n' > $W/home/.gitconfig
  env $ENVS $S/run_kicad.sh $PKG $W/home $W/p/a/board.kicad_pcb $S/$SCN > /dev/null
  echo "===== $N"; [ -n "$VERBOSE" ] && python3 $S/show.py $W/home/result.json | cut -c1-600
  verdict $W/home/result.json "$EXP"
}
run push_basic      k_push_basic.py "" "" "r['remote_head']=='更新 PCB 佈局' and r['clean']"
run push_nff_pull   k_push_nff.py   "teammate"          "NFF_MODE=pull_push" "r['remote_log'][:2]==['nff pull_push','team-change'] and not r['rebase_left']"
run push_nff_force  k_push_nff.py   "teammate"          "NFF_MODE=force" "r['remote_log']==['nff force','init'] and shown_any('Non-Fast-Forward')"
run overwrite       k_overwrite.py  "teammate" "" "r['remote_log']==['overwrite!','init'] and r['ok_label']=='覆蓋遠端' and r['hint_shown']"
run overwrite_block k_overwrite.py  ""                  "OV_BLOCK=1" "r['remote_log']==['init'] and r['draft']=='overwrite!' and shown_any('無法覆蓋')"
run draft           k_draft.py      "" "" "r['draft_saved']=='半成品訊息' and r['restored']=='半成品訊息' and r['after_clear']=='' and r['draft_after_clear']==''"
run pull_conflict_overwrite k_pull.py "conflict"        "PULL_ANSWER=overwrite" "r['board_text']==['TEAM'] and not r['merging'] and r['status']=='' and shown_any('衝突')"
run pull_conflict_keep      k_pull.py "conflict"        "PULL_ANSWER=keep" "r['board_text']==['MINE'] and not r['merging'] and r['head']=='mine-change'"
run pull_dirty_overwrite    k_pull.py "teammate dirty"  "PULL_ANSWER=overwrite" "r['board_text']==['TEAM'] and r['status']=='' and r['head']=='team-change'"
run pull_dirty_keep         k_pull.py "teammate dirty"  "PULL_ANSWER=keep" "r['board_text']==['DIRTY'] and r['head']=='init'"
run status          k_status.py     "lib" "" "r['tabs']==['專案'] and '分支：    main' in r['status_text'][0] and '工作目錄乾淨' in r['status_text'][0]"
run nogit           k_nogit.py      "nogit" "" "shown_any('尚未初始化為 Git')"
run settings        k_settings.py   "lib" "" "r['push_targets']==['ALL','主板專案','元件庫'] and r['remote1name']=='主板專案' and r['scope']=='global' and r['global_restored'][0]=='元件庫' and r['still_open_after_stay'] and r['project_remote2name']==''"
run batch           k_batch.py      "" "" "r['r1_remote'].startswith('批次更新') and 'r1 — ok' in r['batch_push_log'] and 'r2 — ok' in r['batch_push_log'] and 'r1 — ok' in r['batch_pull_log']"
run pull_merge      k_pull.py       "teammate otherfile" "" "r['board_text']==['TEAM'] and r['other_file'] and r['parents']==2 and not r['merging'] and r['shown']==[]"
run stale           k_stale.py      "teammate" "" "r['remote_has_TEAM'] and not r['remote_has_ORIGINAL'] and shown_any('PCB 尚未重新載入')"
# auto-update from a local fake GitHub, then restart KiCad and read its plugin-loader report
if echo update | grep -qE "$F"; then
  SRV=$WORK/srv; mkdir -p $SRV; echo '{"tag_name":"v9.9.9"}' > $SRV/api.json; echo "# README" > $SRV/README.md
  (cd $S/../.. && git archive --format=zip --prefix=RTnexen_PPS_Tool-9.9.9/ HEAD -o $SRV/v9.9.9.zip)
  PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
  (cd $SRV && exec python3 -m http.server $PORT --bind 127.0.0.1 >/dev/null 2>&1) & SP=$!; sleep 1
  export PPS_UPDATE_PORT=$PORT
  for MODE in auto manual; do
    W=$WORK/update_$MODE; rm -rf $W; mkdir -p $W/home; ${PYTHON:-python3} $S/mkproj.py $W/p; printf '[user]\nemail=t@t\nname=T\n' > $W/home/.gitconfig
    UPDATE_MODE=$MODE $S/run_kicad.sh $PKG $W/home $W/p/a/board.kicad_pcb $S/k_update.py >/dev/null
    echo "===== update_$MODE"
    verdict $W/home/result.json "r['steps']==(['UpdateDialog'] if r['mode']=='auto' else ['MainMenuDialog','SettingsDialog','UpdateDialog']) and 'rtnexen_git_tools' in r['plugins_dir_entries'] and not [e for e in r['plugins_dir_entries'] if 'backup' in e or e.startswith('.')] and len(r['backups_dir'])==1 and r['backups_dir'][0].startswith('rtnexen_git_tools_v') and shown_any('更新完成') and not shown_any('自動更新失敗')"
    cp $W/home/result.json $W/home/result_update.json
    $S/run_kicad_keep.sh $W/home $W/p/a/board.kicad_pcb $S/k_loadcheck.py
    echo "===== update_${MODE}: KiCad restart"
    verdict $W/home/result.json "r['load_errors']==[] and 'rtnexen_git_tools' in r['rtnexen_modules'] and not [l for l in r['not_loaded'] if 'rtnexen' in l]"
  done
  kill $SP
fi
echo; echo "KiCad end-to-end: $PASSN PASS, $FAILN FAIL"; [ $FAILN -eq 0 ]
