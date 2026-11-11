from kdrv import *
from rtnexen_git_tools.common import ID_BACK
def st(d):
    if not d.close_btn.IsEnabled(): return False
    RES["tabs"] = [d.notebook.GetPageText(i) for i in range(d.notebook.GetPageCount())]
    RES["status_text"] = [l.GetValue() for l in d.logs]
    click(btn_id(d, ID_BACK))
Driver([("MainMenuDialog", lambda d: click(btn_label(d, "Status"))), ("StatusDialog", st),
        ("MainMenuDialog", lambda d: click(btn_id(d, wx.ID_CANCEL)))])
def main():
    run_plugin(); done()
wx.CallAfter(main)
