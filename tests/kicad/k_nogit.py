from kdrv import *
Driver([("MainMenuDialog", lambda d: (click(btn_label(d, "Push")), wx.CallLater(800, lambda: click(btn_id(d, wx.ID_CANCEL)))))])
def main():
    run_plugin(); done()
wx.CallAfter(main)
