import wx
import json
import threading

from .i18n import (
    t, get_language, set_language, get_global_remote2, set_global_remote2,
    get_config_snapshot, import_config_snapshot,
    LANG_ZH, LANG_EN,
)
from .common import (
    VERSION, APPNAME, _run, is_git_repo, get_remote2_scope, get_remote2_config,
    get_dialog_size, center_on_screen,
)

# ── Settings Dialog ───────────────────────────────────────────────────────────

class SettingsDialog(wx.Dialog):
    def __init__(self, project_path):
        super().__init__(None, title=f"{APPNAME} — {t('subtitle_settings')}",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                         size=get_dialog_size(0.48, 0.74))
        self.project_path = project_path

        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        scroll = wx.ScrolledWindow(self, style=wx.VSCROLL)
        scroll.SetScrollRate(0, 20)
        panel = scroll
        sizer = wx.BoxSizer(wx.VERTICAL)

        # ── Language ──
        self.lang_radio = wx.RadioBox(panel, label=t("label_language"),
                                       choices=["中文", "English"],
                                       majorDimension=2, style=wx.RA_SPECIFY_COLS)
        self.lang_radio.SetSelection(0 if get_language() == LANG_ZH else 1)
        sizer.Add(self.lang_radio, 0, wx.EXPAND | wx.ALL, 12)

        # ── Remote 1 (this project) ──
        box1 = wx.StaticBox(panel, label=t("settings_remote1_box"))
        bs1 = wx.StaticBoxSizer(box1, wx.VERTICAL)
        grid1 = wx.FlexGridSizer(cols=2, hgap=12, vgap=10)
        grid1.AddGrowableCol(1, 1)

        grid1.Add(wx.StaticText(panel, label=t("label_name")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.name1_ctrl = wx.TextCtrl(panel, value="")
        self.name1_ctrl.SetHint(t("default_remote1_name"))
        grid1.Add(self.name1_ctrl, 1, wx.EXPAND)

        grid1.Add(wx.StaticText(panel, label=t("label_local_path")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.path1_lbl = wx.StaticText(panel, label=project_path)
        grid1.Add(self.path1_lbl, 1, wx.EXPAND)

        grid1.Add(wx.StaticText(panel, label=t("label_remote_url")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.url1_ctrl = wx.TextCtrl(panel, value=t("loading"))
        grid1.Add(self.url1_ctrl, 1, wx.EXPAND)

        bs1.Add(grid1, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(bs1, 0, wx.EXPAND | wx.ALL, 12)

        # ── Remote 2 (independent local repo, e.g. component library) ──
        box2 = wx.StaticBox(panel, label=t("settings_remote2_box"))
        bs2 = wx.StaticBoxSizer(box2, wx.VERTICAL)

        self.scope_radio = wx.RadioBox(panel, label=t("label_scope"),
                                        choices=[t("scope_project"), t("scope_global")],
                                        majorDimension=2, style=wx.RA_SPECIFY_COLS)
        self.scope_radio.Bind(wx.EVT_RADIOBOX, self._on_scope_change)
        bs2.Add(self.scope_radio, 0, wx.EXPAND | wx.ALL, 8)

        grid2 = wx.FlexGridSizer(cols=2, hgap=12, vgap=10)
        grid2.AddGrowableCol(1, 1)

        grid2.Add(wx.StaticText(panel, label=t("label_name")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.name2_ctrl = wx.TextCtrl(panel, value="")
        grid2.Add(self.name2_ctrl, 1, wx.EXPAND)

        grid2.Add(wx.StaticText(panel, label=t("label_local_path")), 0, wx.ALIGN_CENTER_VERTICAL)
        path2_row = wx.BoxSizer(wx.HORIZONTAL)
        self.path2_ctrl = wx.TextCtrl(panel, value="")
        path2_row.Add(self.path2_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        browse_btn = wx.Button(panel, label=t("browse"), size=(70, -1))
        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        path2_row.Add(browse_btn, 0)
        grid2.Add(path2_row, 1, wx.EXPAND)

        grid2.Add(wx.StaticText(panel, label=t("label_remote_url")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.url2_ctrl = wx.TextCtrl(panel, value="")
        grid2.Add(self.url2_ctrl, 1, wx.EXPAND)

        bs2.Add(grid2, 1, wx.EXPAND | wx.ALL, 10)
        hint2 = wx.StaticText(panel, label=t("remote2_hint"))
        hint2.SetForegroundColour(wx.Colour(140, 140, 140))
        bs2.Add(hint2, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        sizer.Add(bs2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        apply_btn = wx.Button(panel, label=t("apply"))
        apply_btn.Bind(wx.EVT_BUTTON, self._apply)
        sizer.Add(apply_btn, 0, wx.LEFT | wx.BOTTOM, 22)

        branch_row = wx.BoxSizer(wx.HORIZONTAL)
        branch_row.Add(wx.StaticText(panel, label=t("current_branch")),
                        0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.branch_lbl = wx.StaticText(panel, label=t("loading"))
        branch_row.Add(self.branch_lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(branch_row, 0, wx.LEFT | wx.BOTTOM, 22)

        backup_box = wx.StaticBox(panel, label=t("settings_backup_box"))
        backup_s = wx.StaticBoxSizer(backup_box, wx.VERTICAL)
        backup_row = wx.BoxSizer(wx.HORIZONTAL)
        export_btn = wx.Button(panel, label=t("export_settings"))
        export_btn.Bind(wx.EVT_BUTTON, self._on_export_settings)
        backup_row.Add(export_btn, 0, wx.RIGHT, 8)
        import_btn = wx.Button(panel, label=t("import_settings"))
        import_btn.Bind(wx.EVT_BUTTON, self._on_import_settings)
        backup_row.Add(import_btn, 0)
        backup_s.Add(backup_row, 0, wx.ALL, 8)
        backup_hint = wx.StaticText(panel, label=t("settings_backup_hint"))
        backup_hint.SetForegroundColour(wx.Colour(140, 140, 140))
        backup_s.Add(backup_hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(backup_s, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        info = wx.StaticBox(panel, label=t("about"))
        info_s = wx.StaticBoxSizer(info, wx.VERTICAL)
        info_s.Add(wx.StaticText(panel, label=f"{APPNAME}  v{VERSION}"), 0, wx.ALL, 8)
        info_s.Add(wx.StaticText(panel, label="rtnexen@gmail.com"),
                   0, wx.LEFT | wx.BOTTOM, 8)
        sizer.Add(info_s, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        panel.SetSizer(sizer)
        scroll.FitInside()
        outer_sizer.Add(scroll, 1, wx.EXPAND)

        # ── Bottom buttons (fixed, outside the scroll area so they're
        # always reachable even if the settings above overflow) ──
        bottom = wx.Panel(self)
        row = wx.BoxSizer(wx.HORIZONTAL)
        back_btn = wx.Button(bottom, wx.ID_CANCEL, t("back"), size=(100, 32))
        back_btn.Bind(wx.EVT_BUTTON, self._on_back_or_close)
        row.Add(back_btn, 0)
        row.AddStretchSpacer()
        save_btn = wx.Button(bottom, wx.ID_SAVE, t("save"), size=(90, 32))
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        row.Add(save_btn, 0, wx.RIGHT, 10)
        close_btn = wx.Button(bottom, wx.ID_OK, t("close"), size=(90, 32))
        close_btn.Bind(wx.EVT_BUTTON, self._on_back_or_close)
        row.Add(close_btn, 0)
        bottom.SetSizer(row)
        outer_sizer.Add(bottom, 0, wx.EXPAND | wx.ALL, 12)

        self.SetSizer(outer_sizer)
        self.Layout()
        center_on_screen(self)

        self.Bind(wx.EVT_CLOSE, self._on_dialog_close)

        # Per-scope draft cache for Remote 2 fields, so toggling
        # "label_scope" does not silently discard unsaved edits.
        self._remote2_drafts = {}
        self._current_scope = "project"

        # Updated once the initial async load completes (_populate) and
        # again after every successful Apply/Save — compared against
        # _snapshot() to detect unsaved changes on Back/Close/[X].
        self._saved_snapshot = self._snapshot()

        wx.CallAfter(self._load_async)

    def _snapshot(self):
        return (
            self.lang_radio.GetSelection(),
            self.name1_ctrl.GetValue(),
            self.url1_ctrl.GetValue(),
            self.scope_radio.GetSelection(),
            self.name2_ctrl.GetValue(),
            self.path2_ctrl.GetValue(),
            self.url2_ctrl.GetValue(),
        )

    def _confirm_discard(self):
        if self._snapshot() == self._saved_snapshot:
            return True
        dlg = wx.MessageDialog(self, t("unsaved_changes_msg"),
                                f"{APPNAME} — {t('unsaved_changes_title')}",
                                wx.YES_NO | wx.ICON_WARNING)
        dlg.SetYesNoLabels(t("discard"), t("stay"))
        result = dlg.ShowModal()
        dlg.Destroy()
        return result == wx.ID_YES

    def _on_back_or_close(self, event):
        if self._confirm_discard():
            self.EndModal(event.GetId())

    def _on_dialog_close(self, event):
        if self._confirm_discard():
            self.EndModal(wx.ID_CANCEL)
        else:
            event.Veto()

    def _on_save(self, event):
        self._apply(event)
        self.EndModal(wx.ID_SAVE)

    def _on_export_settings(self, event):
        dlg = wx.FileDialog(self, t("export_settings"),
                             defaultFile="rtnexen_pps_tool_settings.json",
                             wildcard="JSON (*.json)|*.json",
                             style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(get_config_snapshot(), f, ensure_ascii=False, indent=2)
                wx.MessageBox(t("export_settings_ok", path=path), APPNAME, wx.OK | wx.ICON_INFORMATION)
            except OSError as e:
                wx.MessageBox(t("export_settings_fail", err=str(e)), APPNAME, wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def _on_import_settings(self, event):
        dlg = wx.FileDialog(self, t("import_settings"),
                             wildcard="JSON (*.json)|*.json",
                             style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        path = dlg.GetPath()
        dlg.Destroy()

        confirm = wx.MessageDialog(self, t("import_confirm_msg"),
                                    f"{APPNAME} — {t('import_confirm_title')}",
                                    wx.YES_NO | wx.ICON_WARNING)
        confirm.SetYesNoLabels(t("ok"), t("cancel"))
        proceed = confirm.ShowModal() == wx.ID_YES
        confirm.Destroy()
        if not proceed:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            import_config_snapshot(cfg)
        except (OSError, ValueError) as e:
            wx.MessageBox(t("import_settings_fail", err=str(e)), APPNAME, wx.OK | wx.ICON_ERROR)
            return

        self.lang_radio.SetSelection(0 if get_language() == LANG_ZH else 1)
        self._remote2_drafts = {}
        wx.CallAfter(self._load_async)
        wx.MessageBox(t("import_settings_ok"), APPNAME, wx.OK | wx.ICON_INFORMATION)

    def _on_browse(self, event):
        dlg = wx.DirDialog(self, t("browse"),
                            defaultPath=self.path2_ctrl.GetValue() or self.project_path)
        if dlg.ShowModal() == wx.ID_OK:
            self.path2_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _load_async(self):
        path = self.project_path
        def worker():
            name1 = _run(["git", "config", "--get", "rtnexen.remote1name"], path).stdout.strip()
            url1 = _run(["git", "remote", "get-url", "origin"], path)
            url1 = url1.stdout.strip() if url1.returncode == 0 else ""

            scope = get_remote2_scope(path)
            name2, path2 = get_remote2_config(path)
            url2 = ""
            if path2 and is_git_repo(path2):
                u2 = _run(["git", "remote", "get-url", "origin"], path2)
                url2 = u2.stdout.strip() if u2.returncode == 0 else ""

            branch = _run(["git", "branch", "--show-current"], path)
            wx.CallAfter(self._populate, name1, url1, scope, name2, path2, url2,
                          branch.stdout.strip() or t("branch_unknown"))
        threading.Thread(target=worker, daemon=True).start()

    def _populate(self, name1, url1, scope, name2, path2, url2, branch):
        self.name1_ctrl.SetValue(name1)
        self.url1_ctrl.SetValue(url1)
        self.branch_lbl.SetLabel(branch)
        # Guard against the (rare) race where the user toggles the scope
        # radio before this initial async load completes — don't clobber
        # a scope/draft the user already chose.
        if not self._remote2_drafts:
            self.scope_radio.SetSelection(1 if scope == "global" else 0)
            self._current_scope = scope
            self._remote2_drafts[scope] = (name2, path2, url2)
            self.name2_ctrl.SetValue(name2)
            self.path2_ctrl.SetValue(path2)
            self.url2_ctrl.SetValue(url2)
            self._saved_snapshot = self._snapshot()

    def _on_scope_change(self, event):
        new_scope = "global" if self.scope_radio.GetSelection() == 1 else "project"
        old_scope = self._current_scope
        if new_scope == old_scope:
            return
        # Stash whatever is currently in the fields (even unsaved edits)
        # under the scope we're leaving, so switching back restores them —
        # the two scopes' data/drafts never overwrite each other.
        self._remote2_drafts[old_scope] = (
            self.name2_ctrl.GetValue(), self.path2_ctrl.GetValue(), self.url2_ctrl.GetValue(),
        )
        self._current_scope = new_scope

        draft = self._remote2_drafts.get(new_scope)
        if draft is not None:
            self._set_remote2_fields(*draft)
            return

        path = self.project_path
        def worker():
            if new_scope == "global":
                name2, path2 = get_global_remote2()
            else:
                name2 = _run(["git", "config", "--get", "rtnexen.remote2name"], path).stdout.strip()
                path2 = _run(["git", "config", "--get", "rtnexen.remote2path"], path).stdout.strip()
            url2 = ""
            if path2 and is_git_repo(path2):
                u2 = _run(["git", "remote", "get-url", "origin"], path2)
                url2 = u2.stdout.strip() if u2.returncode == 0 else ""
            wx.CallAfter(self._apply_scope_fetch, new_scope, name2, path2, url2)
        threading.Thread(target=worker, daemon=True).start()

    def _apply_scope_fetch(self, scope, name2, path2, url2):
        self._remote2_drafts[scope] = (name2, path2, url2)
        if self._current_scope == scope:
            self._set_remote2_fields(name2, path2, url2)

    def _set_remote2_fields(self, name2, path2, url2):
        self.name2_ctrl.SetValue(name2)
        self.path2_ctrl.SetValue(path2)
        self.url2_ctrl.SetValue(url2)

    def _confirm_global_change(self):
        dlg = wx.MessageDialog(self, t("global_change_warning"),
                                f"{APPNAME} — {t('global_change_warning_title')}",
                                wx.YES_NO | wx.ICON_WARNING)
        dlg.SetYesNoLabels(t("ok"), t("cancel"))
        result = dlg.ShowModal()
        dlg.Destroy()
        return result == wx.ID_YES

    def _apply(self, event):
        results = []
        path = self.project_path

        # ── Language ──
        new_lang = LANG_ZH if self.lang_radio.GetSelection() == 0 else LANG_EN
        if new_lang != get_language():
            set_language(new_lang)

        # ── Remote 1 (this project) ──
        name1 = self.name1_ctrl.GetValue().strip()
        url1 = self.url1_ctrl.GetValue().strip()
        effective_name1 = name1 or t("default_remote1_name")

        if not name1:
            results.append(t("r1_name_default", name=effective_name1))
        else:
            _run(["git", "config", "rtnexen.remote1name", name1], path)
            results.append(t("r1_name_saved", name=name1))

        if url1:
            existing = _run(["git", "remote", "get-url", "origin"], path)
            if existing.returncode == 0:
                r = _run(["git", "remote", "set-url", "origin", url1], path)
            else:
                r = _run(["git", "remote", "add", "origin", url1], path)
            if r.returncode == 0:
                results.append(t("r1_url_ok"))
            else:
                results.append(t("r1_url_fail", err=r.stderr.strip()))

        # ── Remote 2 (independent repo) ──
        # Note: rtnexen.remote2scope is only written when a save/clear is
        # actually committed below — never on validation failure or a
        # cancelled global-change confirmation, so an aborted scope switch
        # leaves the previously active scope untouched.
        scope = "global" if self.scope_radio.GetSelection() == 1 else "project"

        name2 = self.name2_ctrl.GetValue().strip()
        path2 = self.path2_ctrl.GetValue().strip()
        url2 = self.url2_ctrl.GetValue().strip()

        if not name2 and not path2 and not url2:
            proceed = True
            if scope == "global":
                old_name, old_path = get_global_remote2()
                if (old_name, old_path) != ("", ""):
                    proceed = self._confirm_global_change()

            if proceed:
                _run(["git", "config", "rtnexen.remote2scope", scope], path)
                if scope == "global":
                    set_global_remote2("", "")
                else:
                    _run(["git", "config", "--unset", "rtnexen.remote2name"], path)
                    _run(["git", "config", "--unset", "rtnexen.remote2path"], path)
                results.append(t("r2_cleared"))
            else:
                results.append(t("r2_global_change_cancelled"))
        elif not name2 or not path2:
            results.append(t("r2_need_both"))
        elif name2 == effective_name1:
            results.append(t("r2_name_conflict", name=name2))
        elif not is_git_repo(path2):
            results.append(t("r2_not_repo", path=path2))
        else:
            proceed = True
            if scope == "global":
                old_name, old_path = get_global_remote2()
                if (old_name, old_path) != (name2, path2):
                    proceed = self._confirm_global_change()

            if proceed:
                _run(["git", "config", "rtnexen.remote2scope", scope], path)
                if scope == "global":
                    set_global_remote2(name2, path2)
                else:
                    _run(["git", "config", "rtnexen.remote2name", name2], path)
                    _run(["git", "config", "rtnexen.remote2path", path2], path)
                results.append(t("r2_saved", name=name2))

                if url2:
                    existing2 = _run(["git", "remote", "get-url", "origin"], path2)
                    if existing2.returncode == 0:
                        r2 = _run(["git", "remote", "set-url", "origin", url2], path2)
                    else:
                        r2 = _run(["git", "remote", "add", "origin", url2], path2)
                    if r2.returncode == 0:
                        results.append(t("r2_url_ok"))
                    else:
                        results.append(t("r2_url_fail", err=r2.stderr.strip()))
            else:
                results.append(t("r2_global_change_cancelled"))

        wx.MessageBox("\n".join(results) if results else t("no_changes"),
                       t("settings"), wx.OK | wx.ICON_INFORMATION)
        self._saved_snapshot = self._snapshot()
