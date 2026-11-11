import os, sys, wx
scn = os.environ.get("PPS_SCENARIO")
if scn:
    def _go():
        sys.path.insert(0, os.path.dirname(scn))
        g = {"__name__": "scenario"}
        try:
            exec(compile(open(scn, encoding="utf-8").read(), scn, "exec"), g)
        except SystemExit: raise
        except Exception:
            import traceback, kdrv; kdrv.done(error=traceback.format_exc())
    wx.CallLater(4000, _go)
