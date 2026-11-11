#!/bin/bash
# usage: run_kicad.sh <plugin_pkg_dir> <home_dir> <board_file> <scenario.py>
set -e
PKG=$1; H=$2; BOARD=$3; SCN=$4; HERE=$(cd $(dirname $0); pwd)
C=$H/.config/kicad/7.0; mkdir -p $C/scripting/plugins
printf '(fp_lib_table\n  (version 7)\n)\n' > $C/fp-lib-table
printf '(sym_lib_table\n  (version 7)\n)\n' > $C/sym-lib-table
echo '{"meta":{"version":3}}' > $C/kicad_common.json
rm -rf $C/scripting/plugins/rtnexen_git_tools; cp -r $PKG $C/scripting/plugins/rtnexen_git_tools
cp $HERE/zz_probe.py $C/scripting/plugins/; cp $HERE/kdrv.py $(dirname $SCN)/ 2>/dev/null || true
rm -f $H/result.json
LANG=C.UTF-8 NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost HOME=$H PPS_SCENARIO=$SCN timeout 120 xvfb-run -a -s "-screen 0 1600x1000x24" pcbnew $BOARD > $H/pcbnew.log 2>&1 || true
cat $H/result.json 2>/dev/null || { echo '{"error":"no result"}'; tail -20 $H/pcbnew.log; }
