import wx
import os
import glob
import threading

from .i18n import t, t_en, get_commit_draft, set_commit_draft, clear_commit_draft
from .common import APPNAME, ID_BACK, _run, get_dialog_size, _build_target_choices, untrack_ignored_files
from .base_dialog import BaseGitDialog
from .status_dialog import _make_dot_bitmap, STATUS_DOT_COLORS

# Draft-status dot colors reuse the same palette/logic as the Status tab:
#   grey   — commit box empty
#   yellow — has text, not yet saved as a draft
#   green  — current text matches the saved draft
DRAFT_DOT_COLORS = {
    "empty":   STATUS_DOT_COLORS[None],
    "unsaved": STATUS_DOT_COLORS["dirty"],
    "saved":   STATUS_DOT_COLORS["clean"],
}

# ── Unsaved design file detection ─────────────────────────────────────────────
# KiCad writes a "_autosave-<filename>" backup file while a schematic/PCB
# editor has unsaved changes in memory. If that autosave file is newer than
# the real, saved file, the editor most likely still holds unsaved edits —
# there is no direct API to query Eeschema's in-memory state from a pcbnew
# ActionPlugin process, so this mtime comparison is the best available signal.

def check_unsaved_design_files(project_path):
    """Return a list of project-relative filenames that look like they have
    unsaved changes in their editor (schematic and/or PCB). Searches
    recursively so hierarchical sub-sheets kept in subfolders are covered too."""
    warnings = []
    for ext in ("kicad_sch", "kicad_pcb"):
        for real in glob.glob(os.path.join(project_path, "**", f"*.{ext}"), recursive=True):
            d, fname = os.path.split(real)
            autosave = os.path.join(d, f"_autosave-{fname}")
            if os.path.isfile(autosave) and os.path.getmtime(autosave) > os.path.getmtime(real):
                warnings.append(os.path.relpath(real, project_path))
    return warnings

# ── Push Form Dialog ──────────────────────────────────────────────────────────

class PushDialog(BaseGitDialog):
    def __init__(self, project_path):
        super().__init__(t_en("subtitle_push"), project_path,
                         size=get_dialog_size(0.48, 0.82))
        p  = self.panel
        cs = self.content_sizer

        choices, self.targets = _build_target_choices(project_path)
        self._kind_paths = {cfg["kind"]: cfg["path"] for cfg in self.targets}

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
        self.dot_bitmaps = {}
        self._saved_values = {}
        for kind, label_key, presets in (("project", "commit_message_project", project_presets),
                                          ("library", "commit_message_library", library_presets)):
            panel_k = wx.Panel(p)
            sizer_k = wx.BoxSizer(wx.VERTICAL)

            sizer_k.Add(wx.StaticText(panel_k, label=t(label_key)), 0, wx.BOTTOM, 4)

            msg_ctrl = wx.TextCtrl(panel_k, style=wx.TE_MULTILINE, size=(-1, 60))
            msg_ctrl.SetFont(
                wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            msg_ctrl.Bind(wx.EVT_TEXT, lambda e, k=kind: self._update_dot(k))
            sizer_k.Add(msg_ctrl, 0, wx.EXPAND | wx.BOTTOM, 4)

            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            for text in presets:
                b = wx.Button(panel_k, label=text, size=(-1, 30))
                b.Bind(wx.EVT_BUTTON, lambda e, txt=text, mc=msg_ctrl: self._append_msg(mc, txt))
                row_sizer.Add(b, 1, wx.RIGHT, 4)
            sizer_k.Add(row_sizer, 0, wx.EXPAND | wx.BOTTOM, 4)

            clear_row = wx.BoxSizer(wx.HORIZONTAL)
            clear_row.AddStretchSpacer()
            dot_bmp = wx.StaticBitmap(panel_k, bitmap=_make_dot_bitmap(DRAFT_DOT_COLORS["empty"]))
            clear_row.Add(dot_bmp, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            save_btn = wx.Button(panel_k, label=t("btn_save_draft"), size=(-1, 28))
            save_btn.Bind(wx.EVT_BUTTON, lambda e, mc=msg_ctrl, k=kind: self._on_save_draft(mc, k))
            clear_row.Add(save_btn, 0, wx.RIGHT, 6)
            clear_btn = wx.Button(panel_k, label=t("clear"), size=(-1, 28))
            clear_btn.Bind(wx.EVT_BUTTON, lambda e, mc=msg_ctrl, k=kind: self._on_clear(mc, k))
            clear_row.Add(clear_btn, 0)
            sizer_k.Add(clear_row, 0, wx.EXPAND)

            panel_k.SetSizer(sizer_k)
            self.msg_panels[kind] = panel_k
            self.msg_ctrls[kind] = msg_ctrl
            self.dot_bitmaps[kind] = dot_bmp
            cs.Add(panel_k, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        self.add_bottom_buttons(t("btn_push_submit"))
        self.FinalizeLayout()
        self._update_msg_panels()
        self._load_drafts()
        self._intercept_close_buttons()
        wx.CallAfter(self._load_async)

    def _load_drafts(self):
        """Pre-fill commit message boxes with any previously saved draft for
        that target's repo path (survives plugin/dialog close), and record
        the baseline used to detect unsaved edits."""
        for kind, ctrl in self.msg_ctrls.items():
            path = self._kind_paths.get(kind)
            draft = get_commit_draft(path) if path else ""
            self._saved_values[kind] = draft
            if draft:
                ctrl.SetValue(draft)
            self._update_dot(kind)

    # ── Draft status dot ───────────────────────────────────────────────────

    def _draft_state(self, kind):
        current = self.msg_ctrls[kind].GetValue()
        if not current.strip():
            return "empty"
        if current == self._saved_values.get(kind, ""):
            return "saved"
        return "unsaved"

    def _update_dot(self, kind):
        state = self._draft_state(kind)
        self.dot_bitmaps[kind].SetBitmap(_make_dot_bitmap(DRAFT_DOT_COLORS[state]))

    def _has_unsaved_drafts(self):
        return any(self._draft_state(k) == "unsaved" for k in self.msg_ctrls)

    def _save_all_drafts(self):
        for kind, ctrl in self.msg_ctrls.items():
            path = self._kind_paths.get(kind)
            if not path:
                continue
            set_commit_draft(path, ctrl.GetValue())
            self._saved_values[kind] = ctrl.GetValue()
            self._update_dot(kind)

    # ── Close interception (Back / Cancel / [X]) ──────────────────────────

    def _intercept_close_buttons(self):
        self.back_btn.Unbind(wx.EVT_BUTTON)
        self.back_btn.Bind(wx.EVT_BUTTON, lambda e: self._attempt_close(ID_BACK))
        cancel_btn = self.FindWindowById(wx.ID_CANCEL)
        if cancel_btn:
            cancel_btn.Bind(wx.EVT_BUTTON, lambda e: self._attempt_close(wx.ID_CANCEL))
        self.Bind(wx.EVT_CLOSE, self._on_close_event)

    def _ask_close_confirm(self):
        """Returns 'back', 'save', or 'discard'."""
        dlg = wx.MessageDialog(self, t("draft_close_confirm_msg"),
                                f"{APPNAME} — {t('draft_close_confirm_title')}",
                                wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
        dlg.SetYesNoCancelLabels(t("btn_close_back"), t("btn_close_save"), t("btn_close_discard"))
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_YES:
            return "back"
        if result == wx.ID_NO:
            return "save"
        return "discard"

    def _attempt_close(self, end_id):
        if self._has_unsaved_drafts():
            choice = self._ask_close_confirm()
            if choice == "back":
                return
            if choice == "save":
                self._save_all_drafts()
        self.EndModal(end_id)

    def _on_close_event(self, event):
        if self._has_unsaved_drafts():
            choice = self._ask_close_confirm()
            if choice == "back":
                event.Veto()
                return
            if choice == "save":
                self._save_all_drafts()
        self.EndModal(wx.ID_CANCEL)

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

    def _on_save_draft(self, msg_ctrl, kind):
        path = self._kind_paths.get(kind)
        if not path:
            return
        set_commit_draft(path, msg_ctrl.GetValue())
        self._saved_values[kind] = msg_ctrl.GetValue()
        self._update_dot(kind)

    def _on_clear(self, msg_ctrl, kind):
        if not msg_ctrl.GetValue():
            return
        dlg = wx.MessageDialog(self, t("clear_confirm_msg"),
                                f"{APPNAME} — {t('clear_confirm_title')}",
                                wx.YES_NO | wx.ICON_WARNING)
        dlg.SetYesNoLabels(t("ok"), t("cancel"))
        if dlg.ShowModal() == wx.ID_YES:
            msg_ctrl.SetValue("")
            msg_ctrl.SetFocus()
            path = self._kind_paths.get(kind)
            if path:
                clear_commit_draft(path)
                self._saved_values[kind] = ""
            self._update_dot(kind)
        dlg.Destroy()

    def _load_async(self):
        path = self.project_path
        def worker():
            if get_commit_draft(path):
                return  # don't clobber a restored draft with the branch-name default
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
    clear_commit_draft(path)
