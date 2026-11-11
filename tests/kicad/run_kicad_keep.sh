#!/bin/bash
# like run_kicad.sh but does NOT reinstall the plugin (second start after an update)
H=$1; BOARD=$2; SCN=$3; rm -f $H/result.json
NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost HOME=$H PPS_SCENARIO=$SCN timeout 120 xvfb-run -a -s "-screen 0 1600x1000x24" pcbnew $BOARD > $H/pcbnew2.log 2>&1 || true
