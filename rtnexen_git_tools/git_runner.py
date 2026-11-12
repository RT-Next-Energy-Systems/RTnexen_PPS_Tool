import wx

from .i18n import t, t_en, set_commit_draft
from .common import VERSION, APPNAME, ID_BACK, save_open_board, watch_open_board

from .main_menu_dialog import MainMenuDialog
from .push_dialog import PushDialog, _push_fn, check_unsaved_design_files
from .pull_dialog import PullDialog, _pull_all_fn
from .operation_dialog import OperationDialog
from .status_dialog import StatusDialog

# ── Public entry points ───────────────────────────────────────────────────────

def run_push(project_path):
    unsaved = check_unsaved_design_files(project_path)
    if unsaved:
        msg = t("unsaved_design_msg", files="\n".join(f"  • {f}" for f in unsaved))
        confirm = wx.MessageDialog(None, msg, f"{APPNAME} — {t('unsaved_design_title')}",
                                    wx.YES_NO | wx.ICON_WARNING)
        confirm.SetYesNoLabels(t("ok"), t("cancel"))
        proceed = confirm.ShowModal() == wx.ID_YES
        confirm.Destroy()
        if not proceed:
            return

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
        # Keep whatever the user did type (e.g. the project message when only
        # the library one is empty) instead of silently discarding it.
        for cfg in targets:
            if messages.get(cfg["kind"], "").strip():
                set_commit_draft(cfg["path"], messages[cfg["kind"]])
        wx.MessageBox(t("commit_msg_empty"), t("cancelled"),
                      wx.OK | wx.ICON_WARNING)
        return

    if save_open_board() == "stale":
        # A Pull updated the open .kicad_pcb and the editor hasn't saved since:
        # saving the in-memory (old) board would revert the pulled changes.
        wx.MessageBox(t("stale_board_msg"), f"{APPNAME} — {t('stale_board_title')}",
                      wx.OK | wx.ICON_WARNING)

    _push_fn._messages = messages
    _push_fn._targets = targets
    op = OperationDialog(t_en("subtitle_push"), project_path, _push_fn)
    # "Pull & Push" (rebase) can rewrite the open .kicad_pcb on disk too.
    opres = watch_open_board(op.ShowModal)
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
    opres = watch_open_board(op.ShowModal)
    op.Destroy()
    if opres == ID_BACK:
        run_main_dialog(project_path)

def run_status(project_path):
    dlg = StatusDialog(project_path)
    result = dlg.ShowModal()
    dlg.Destroy()
    if result == ID_BACK:
        run_main_dialog(project_path)

_update_check_started = False

def run_main_dialog(project_path):
    # Background check for a newer release, once per KiCad session (honours
    # "Skip this version"). It was implemented but never called before.
    global _update_check_started
    if not _update_check_started:
        _update_check_started = True
        from . import update_check
        update_check.check_for_update_async(VERSION)
    dlg = MainMenuDialog(project_path)
    dlg.ShowModal()
    dlg.Destroy()
