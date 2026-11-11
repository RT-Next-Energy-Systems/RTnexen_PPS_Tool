# Fresh KiCad start: what did KiCad's own plugin loader report?
from kdrv import *
done(not_loaded=pcbnew.NOT_LOADED_WIZARDS.splitlines(), load_errors=pcbnew.FULL_BACK_TRACE.strip().splitlines()[-3:],
     rtnexen_modules=sorted(m for m in sys.modules if m.startswith("rtnexen")))
