import wx
import os
import threading

from .i18n import t, t_en
from .common import APPNAME, _run, get_dialog_size, _build_target_choices, untrack_ignored_files
from .base_dialog import BaseGitDialog

# ── Push Form Dialog ──────────────────────────────────────────────────────────

class PushDialog(BaseGitDialog):
    def __init__(self, project_path):
        super().__init__(t_en("subtitle_push"), project_path,
                         size=get_dialog_size(0.48, 0.82))
        p  = self.panel
        cs = self.content_sizer

        choices, self.targets = _build_target_choices(project_path)

        cs.AddSpacer(14)
        self.target_radio = wx.RadioBox(p, label=t("target"),
                                         choices=choices,
                                         majorDimension=len(choices),
                                         style=wx.RA_SPECIFY_COLS)
        self.target_radio.Bind(wx.EVT_RADIOBOX, self._on_target_change)
        cs.Add(self.target_radio, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        cs.Add(wx.StaticText(p, label=t("changed_files")), 0, wx.LEFT | wx.TOP, 14)
        self.status_text = wx.TextCtrl(p,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL, size=(-1, 160))
        self.status_text.SetFont(
            wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.status_text.SetValue(t("loading"))
        cs.Add(self.status_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        # ── Per-kind commit message panels (one per target "kind"; shown/
        # hidden based on which target(s) are currently selected) ──
        project_presets = [t("quick_update_schematic"), t("quick_update_pcb"),
                            t("quick_add_component"), t("quick_fix_drc")]
        library_presets = [t("quick_lib_add"), t("quick_lib_modify"),
                            t("quick_lib_remove"), t("quick_lib_update")]

        self.msg_panels = {}
        self.msg_ctrls = {}
        for kind, label_key, presets in (("project", "commit_message_project", project_presets),
                                          ("library", "commit_message_library", library_presets)):
            panel_k = wx.Panel(p)
            sizer_k = wx.BoxSizer(wx.VERTICAL)

            sizer_k.Add(wx.StaticText(panel_k, label=t(label_key)), 0, wx.BOTTOM, 4)

            msg_ctrl = wx.TextCtrl(panel_k, style=wx.TE_MULTILINE, size=(-1, 60))
            msg_ctrl.SetFont(
                wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            sizer_k.Add(msg_ctrl, 0, wx.EXPAND | wx.BOTTOM, 4)

            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            for text in presets:
                b = wx.Button(panel_k, label=text, size=(-1, 30))
                b.Bind(wx.EVT_BUTTON, lambda e, txt=text, mc=msg_ctrl: self._append_msg(mc, txt))
                row_sizer.Add(b, 1, wx.RIGHT, 4)
            sizer_k.Add(row_sizer, 0, wx.EXPAND | wx.BOTTOM, 4)

            clear_row = wx.BoxSizer(wx.HORIZONTAL)
            clear_row.AddStretchSpacer()
            clear_btn = wx.Button(panel_k, label=t("clear"), size=(-1, 28))
            clear_btn.Bind(wx.EVT_BUTTON, lambda e, mc=msg_ctrl: self._on_clear(mc))
            clear_row.Add(clear_btn, 0)
            sizer_k.Add(clear_row, 0, wx.EXPAND)

            panel_k.SetSizer(sizer_k)
            self.msg_panels[kind] = panel_k
            self.msg_ctrls[kind] = msg_ctrl
            cs.Add(panel_k, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        self.add_bottom_buttons(t("btn_push_submit"))
        self.FinalizeLayout()
        self._update_msg_panels()
        wx.CallAfter(self._load_async)

    def _selected_targets(self):
        sel = self.target_radio.GetStringSelection()
        if sel == "ALL":
            return list(self.targets)
        return [cfg for cfg in self.targets if cfg["name"] == sel] or [self.targets[0]]

    def _on_target_change(self, event):
        self._refresh_status()
        self._update_msg_panels()

    def _update_msg_panels(self):
        kinds = set(cfg["kind"] for cfg in self._selected_targets())
        for kind, panel in self.msg_panels.items():
            self.content_sizer.Show(panel, kind in kinds, recursive=True)
        self.content_sizer.Layout()
        self.panel.Layout()

    def _append_msg(self, msg_ctrl, text):
        current = msg_ctrl.GetValue()
        if current and not current.endswith((" ", "\n", "\t")):
            current += " "
        msg_ctrl.SetValue(current + text)
        msg_ctrl.SetInsertionPointEnd()
        msg_ctrl.SetFocus()

    def _on_clear(self, msg_ctrl):
        if not msg_ctrl.GetValue():
            return
        dlg = wx.MessageDialog(self, t("clear_confirm_msg"),
                                f"{APPNAME} — {t('clear_confirm_title')}",
                                wx.YES_NO | wx.ICON_WARNING)
        dlg.SetYesNoLabels(t("ok"), t("cancel"))
        if dlg.ShowModal() == wx.ID_YES:
            msg_ctrl.SetValue("")
            msg_ctrl.SetFocus()
        dlg.Destroy()

    def _load_async(self):
        path = self.project_path
        def worker():
            branch = _run(["git", "branch", "--show-current"], path)
            b = branch.stdout.strip()
            if b and b not in ("main", "master", "develop"):
                wx.CallAfter(self.msg_ctrls["project"].SetValue, f"Update {b}")
        threading.Thread(target=worker, daemon=True).start()
        self._refresh_status()

    def _refresh_status(self):
        targets = self._selected_targets()
        def worker():
            parts = []
            for cfg in targets:
                st = _run(["git", "status", "--porcelain"], cfg["path"])
                s = st.stdout.strip() or t("no_changes_push")
                if len(targets) > 1:
                    parts.append(f"── {cfg['name']} ──\n{s}")
                else:
                    parts.append(s)
            wx.CallAfter(self.status_text.SetValue, "\n\n".join(parts))
        threading.Thread(target=worker, daemon=True).start()

    def GetMessages(self):
        return {kind: ctrl.GetValue() for kind, ctrl in self.msg_ctrls.items()}

    def GetTargets(self):
        return self._selected_targets()

# ── .gitignore auto-creation ───────────────────────────────────────────────

GITIGNORE_TEMPLATE = """# KiCad backup & autosave files
*.bak
*-bak.*
_autosave-*
*.kicad_pcb-bak
*.kicad_sch-bak
*.000
fp-info-cache
*.lck

# Python
__pycache__/
*.pyc

# OS
.DS_Store
Thumbs.db

# VS Code Local History
.history/
"""

_REQUIRED_IGNORES = [".history/", "__pycache__/", "*.pyc", ".DS_Store", "Thumbs.db"]

def _ensure_gitignore(log, path):
    gi_path = os.path.join(path, ".gitignore")
    try:
        if not os.path.isfile(gi_path):
            with open(gi_path, "w", encoding="utf-8") as f:
                f.write(GITIGNORE_TEMPLATE)
            log(t("log_gitignore_created"))
        else:
            with open(gi_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            missing = [e for e in _REQUIRED_IGNORES if e not in content]
            if missing:
                with open(gi_path, "a", encoding="utf-8") as f:
                    f.write("\n# Added by RTnexen PPS Tool\n")
                    for e in missing:
                        f.write(e + "\n")
                log(t("log_gitignore_updated"))
    except OSError as e:
        log(t("log_gitignore_failed", err=str(e)))

# ── Git operation functions (run in background thread) ────────────────────────

def _push_fn(log, project_path):
    targets = _push_fn._targets
    messages = _push_fn._messages

    for cfg in targets:
        if len(targets) > 1:
            log(f"\n══════ {cfg['name']} ══════")
        _push_one(log, cfg["path"], messages[cfg["kind"]])

def _push_one(log, path, commit_msg):
    _ensure_gitignore(log, path)

    removed = untrack_ignored_files(path)
    # Also explicitly untrack .history — it may be a nested git repo which
    # git ls-files --ignored does not list on all git versions
    tracked_history = _run(["git", "ls-files", "--cached", "--", ".history"], path)
    if tracked_history.stdout.strip():
        _run(["git", "rm", "-r", "--cached", "--", ".history"], path)
        if ".history" not in removed:
            removed.append(".history")
    if removed:
        log(t("log_untracked_history"))

    log(t("log_staging"))
    r = _run(["git", "add", "-A"], path)
    if r.stdout.strip(): log(r.stdout.strip())

    log(t("log_committing", msg=commit_msg))
    r = _run(["git", "commit", "-m", commit_msg], path)
    if r.stdout.strip(): log(r.stdout.strip())
    if r.returncode != 0:
        err = r.stderr.strip() or r.stdout.strip()
        if "nothing to commit" in err:
            log(t("log_nothing_to_commit"))
        else:
            log(t("log_commit_failed", err=err))
            return

    branch = _run(["git", "branch", "--show-current"], path).stdout.strip()
    log(t("log_pushing"))
    args = ["git", "push", "origin", branch] if branch else ["git", "push", "origin"]
    r = _run(args, path)
    if r.stdout.strip(): log(r.stdout.strip())
    if r.returncode != 0:
        log(t("log_push_failed", err=r.stderr.strip()))
        return
    log(t("log_push_done"))
