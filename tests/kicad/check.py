"""usage: check.py result.json "<python expr over r>"  -> prints PASS/FAIL"""
import json, sys
try:
    r = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    print("FAIL (no result: %s)" % e); sys.exit(1)
if "error" in r:
    print("FAIL (error: %s)" % str(r["error"]).strip().splitlines()[-1][:150]); sys.exit(1)
try:
    ok = eval(sys.argv[2], {}, {"r": r, "shown_any": lambda s: any(s in c or s in m for c, m in r.get("shown", []))})
except Exception as e:
    ok = False; print("expectation error:", e)
print("PASS" if ok else "FAIL  expected: " + sys.argv[2]); sys.exit(0 if ok else 1)
