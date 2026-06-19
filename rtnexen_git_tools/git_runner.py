import wx

from .i18n import t, t_en
from .common import VERSION, APPNAME, ID_BACK

from .main_menu_dialog import MainMenuDialog
from .push_dialog import PushDialog, _push_fn
from .pull_dialog import PullDialog, _pull_all_fn
from .operation_dialog import OperationDialog
from .status_dialog import StatusDialog

# ── Public entry points ───────────────────────────────────────────────────────

def run_push(project_path):
    dlg = PushDialog(project_path)
    result = dlg.ShowModal()
    if result == ID_BACK:
        dlg.Destroy()
        run_main_dialog(project_path)
        return
    if result != wx.ID_OK:
        dlg.Destroy(); return

    messages = dlg.GetMessages()
    targets = dlg.GetTargets()
    dlg.Destroy()

    needed_kinds = set(cfg["kind"] for cfg in targets)
    if any(not messages.get(kind, "").strip() for kind in needed_kinds):
        wx.MessageBox(t("commit_msg_empty"), t("cancelled"),
                      wx.OK | wx.ICON_WARNING)
        return

    try:
        import pcbnew
        board = pcbnew.GetBoard()
        pcbnew.SaveBoard(board.GetFileName(), board)
    except Exception:
        pass

    _push_fn._messages = messages
    _push_fn._targets = targets
    op = OperationDialog(t_en("subtitle_push"), project_path, _push_fn)
    opres = op.ShowModal()
    op.Destroy()
    if opres == ID_BACK:
        run_main_dialog(project_path)

def run_pull(project_path):
    dlg = PullDialog(project_path)
    result = dlg.ShowModal()
    if result == ID_BACK:
        dlg.Destroy()
        run_main_dialog(project_path)
        return
    if result != wx.ID_OK:
        dlg.Destroy(); return

    targets = dlg.GetTargets()
    dlg.Destroy()

    _pull_all_fn._targets = targets
    op = OperationDialog(t_en("subtitle_pull"), project_path, _pull_all_fn)
    opres = op.ShowModal()
    op.Destroy()
    if opres == ID_BACK:
        run_main_dialog(project_path)

def run_status(project_path):
    dlg = StatusDialog(project_path)
    result = dlg.ShowModal()
    dlg.Destroy()
    if result == ID_BACK:
        run_main_dialog(project_path)

def run_main_dialog(project_path):
    dlg = MainMenuDialog(project_path)
    dlg.ShowModal()
    dlg.Destroy()
