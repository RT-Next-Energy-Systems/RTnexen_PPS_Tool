import json
import os

LANG_ZH = "zh"
LANG_EN = "en"

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".rtnexen_pps_tool")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

_cache = None

def _load():
    global _cache
    if _cache is not None:
        return _cache
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except (OSError, ValueError):
            _cache = {}
    else:
        _cache = {}
    return _cache

def _save(cfg):
    global _cache
    _cache = cfg
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def get_language():
    return _load().get("language", LANG_ZH)

def set_language(lang):
    cfg = dict(_load())
    cfg["language"] = lang
    _save(cfg)

def get_global_remote2():
    """Returns (name, path) for the globally-scoped Remote 2, or ("", "")."""
    cfg = _load()
    return cfg.get("remote2_name", ""), cfg.get("remote2_path", "")

def set_global_remote2(name, path):
    cfg = dict(_load())
    cfg["remote2_name"] = name
    cfg["remote2_path"] = path
    _save(cfg)

def get_global_remote2_url():
    """Returns the last-known Remote 2 git remote URL stored in global config."""
    return _load().get("remote2_url", "")

def set_global_remote2_url(url):
    cfg = dict(_load())
    cfg["remote2_url"] = url
    _save(cfg)

def get_skipped_version():
    return _load().get("skipped_version", "")

def set_skipped_version(tag):
    cfg = dict(_load())
    cfg["skipped_version"] = tag
    _save(cfg)

def get_config_snapshot():
    """Return a copy of the entire global config (for export)."""
    return dict(_load())

def import_config_snapshot(cfg):
    """Replace the entire global config (from an imported export file)."""
    if not isinstance(cfg, dict):
        raise ValueError("invalid settings file")
    _save(dict(cfg))

# ── Translation table ──────────────────────────────────────────────────────

STRINGS = {
    # Common
    "back":    {LANG_ZH: "← 返回",   LANG_EN: "← Back"},
    "cancel":  {LANG_ZH: "取消",     LANG_EN: "Cancel"},
    "close":   {LANG_ZH: "關閉",     LANG_EN: "Close"},
    "ok":      {LANG_ZH: "確定",     LANG_EN: "OK"},
    "apply":   {LANG_ZH: "套用",     LANG_EN: "Apply"},
    "settings":{LANG_ZH: "設定",     LANG_EN: "Settings"},
    "loading": {LANG_ZH: "載入中...", LANG_EN: "Loading..."},
    "cancelled": {LANG_ZH: "已取消", LANG_EN: "Cancelled"},
    "no_changes": {LANG_ZH: "沒有變更", LANG_EN: "No changes"},
    "default_remote1_name": {LANG_ZH: "專案", LANG_EN: "Project"},
    "branch_unknown": {LANG_ZH: "未知", LANG_EN: "unknown"},
    "lang_changed_reopen": {
        LANG_ZH: "語言已變更，請關閉並重新開啟此視窗以套用新語言。",
        LANG_EN: "Language changed. Please close and reopen this window to apply the new language.",
    },
    "save": {LANG_ZH: "保存", LANG_EN: "Save"},
    "stay": {LANG_ZH: "返回設定", LANG_EN: "Stay"},
    "discard": {LANG_ZH: "離開（不儲存）", LANG_EN: "Leave (Discard)"},
    "unsaved_changes_title": {LANG_ZH: "尚未儲存的變更", LANG_EN: "Unsaved Changes"},
    "unsaved_changes_msg": {
        LANG_ZH: "您有尚未儲存的變更，離開後這些變更將不會套用。\n\n確定要離開嗎？",
        LANG_EN: "You have unsaved changes that will be lost if you leave.\n\nLeave anyway?",
    },

    # Dialog subtitles
    "subtitle_select_action": {LANG_ZH: "選擇操作", LANG_EN: "Select Action"},
    "subtitle_push":     {LANG_ZH: "Git 推送", LANG_EN: "Git Push"},
    "subtitle_pull":     {LANG_ZH: "Git 拉取", LANG_EN: "Git Pull"},
    "subtitle_status":   {LANG_ZH: "Git 狀態", LANG_EN: "Git Status"},
    "subtitle_settings": {LANG_ZH: "設定",     LANG_EN: "Settings"},

    # Main menu
    "btn_push":   {LANG_ZH: "↑   Push",   LANG_EN: "↑   Push"},
    "btn_pull":   {LANG_ZH: "↓   Pull",   LANG_EN: "↓   Pull"},
    "btn_status": {LANG_ZH: "●   Status", LANG_EN: "●   Status"},
    "tip_push":   {LANG_ZH: "提交並推送變更到遠端", LANG_EN: "Commit & push changes to remote"},
    "tip_pull":   {LANG_ZH: "從遠端拉取最新變更",   LANG_EN: "Pull latest changes from remote"},
    "tip_status": {LANG_ZH: "查看分支、變更與最近紀錄", LANG_EN: "View branch, changes & recent log"},

    # Settings
    "settings_remote1_box": {LANG_ZH: " Remote 1 — 目前專案 ", LANG_EN: " Remote 1 — This Project "},
    "settings_remote2_box": {LANG_ZH: " Remote 2 — 獨立 Repo（例如元件庫） ", LANG_EN: " Remote 2 — Independent Repo (e.g. component library) "},
    "label_name":       {LANG_ZH: "名稱：",     LANG_EN: "Name:"},
    "label_local_path": {LANG_ZH: "本地路徑：", LANG_EN: "Local Path:"},
    "label_remote_url": {LANG_ZH: "Remote URL：", LANG_EN: "Remote URL:"},
    "label_scope":      {LANG_ZH: "儲存範圍：", LANG_EN: "Storage Scope:"},
    "scope_global":  {LANG_ZH: "全域路徑（所有專案共用）", LANG_EN: "Global (shared by all projects)"},
    "scope_project": {LANG_ZH: "專案路徑（僅此專案）",     LANG_EN: "Project-specific (this project only)"},
    "browse": {LANG_ZH: "瀏覽...", LANG_EN: "Browse..."},
    "remote2_hint": {
        LANG_ZH: "此本地路徑必須是另一個獨立的 git repository（與目前專案完全分開）。\n"
                 "兩個 Remote 沒有主從關係，皆可獨立 Push / Pull / Status。",
        LANG_EN: "This local path must be another independent git repository (completely separate from this project).\n"
                 "The two remotes have no primary/secondary relationship — each can be pushed/pulled/checked independently.",
    },
    "label_language": {LANG_ZH: "語言：", LANG_EN: "Language:"},
    "current_branch": {LANG_ZH: "目前分支：", LANG_EN: "Current Branch:"},
    "about": {LANG_ZH: " 關於 ", LANG_EN: " About "},

    "global_change_warning_title": {LANG_ZH: "全域設定變更確認", LANG_EN: "Confirm Global Setting Change"},
    "global_change_warning": {
        LANG_ZH: "此更動會影響此裝置上所有相關設定，\n務必再次確認，送出後無法復原。\n\n是否繼續？",
        LANG_EN: "This change affects all related settings on this device.\n"
                 "Please confirm carefully — it cannot be undone after submitting.\n\nContinue?",
    },

    # Backup & restore (global settings)
    "settings_backup_box": {LANG_ZH: " 備份與還原 ", LANG_EN: " Backup & Restore "},
    "settings_backup_hint": {
        LANG_ZH: "匯出/匯入語言、全域 Remote 2 等全域設定，方便更換電腦時保留。",
        LANG_EN: "Export/import global settings (language, global Remote 2, etc.) — useful when moving to a new computer.",
    },
    "export_settings": {LANG_ZH: "匯出設定...", LANG_EN: "Export Settings..."},
    "import_settings": {LANG_ZH: "匯入設定...", LANG_EN: "Import Settings..."},
    "export_settings_ok":   {LANG_ZH: "設定已匯出至：\n{path}", LANG_EN: "Settings exported to:\n{path}"},
    "export_settings_fail": {LANG_ZH: "匯出失敗：{err}", LANG_EN: "Export failed: {err}"},
    "import_settings_ok":   {LANG_ZH: "設定已匯入並套用。", LANG_EN: "Settings imported and applied."},
    "import_settings_fail": {LANG_ZH: "匯入失敗：{err}", LANG_EN: "Import failed: {err}"},
    "import_confirm_title": {LANG_ZH: "確認匯入設定", LANG_EN: "Confirm Import"},
    "import_confirm_msg": {
        LANG_ZH: "匯入將覆蓋目前的全域設定（語言、全域 Remote 2、已跳過版本等），是否繼續？",
        LANG_EN: "Importing will overwrite your current global settings (language, global Remote 2, skipped version, etc.). Continue?",
    },

    # Settings apply results
    "r1_name_default": {LANG_ZH: "Remote 1：使用預設名稱（'{name}'）", LANG_EN: "Remote 1: using default name ('{name}')"},
    "r1_name_saved": {LANG_ZH: "Remote 1（'{name}'）：名稱已儲存", LANG_EN: "Remote 1 ('{name}'): name saved"},
    "r1_git_init_ok":   {LANG_ZH: "已自動執行 git init 並設定 Remote 1 URL", LANG_EN: "git init completed and Remote 1 URL set"},
    "r1_git_init_fail": {LANG_ZH: "git init 失敗：{err}", LANG_EN: "git init failed: {err}"},
    "r1_url_ok":     {LANG_ZH: "Remote 1 URL：OK", LANG_EN: "Remote 1 URL: OK"},
    "r1_url_fail":   {LANG_ZH: "Remote 1 URL：失敗 - {err}", LANG_EN: "Remote 1 URL: failed - {err}"},
    "r2_cleared":    {LANG_ZH: "Remote 2：已清除", LANG_EN: "Remote 2: cleared"},
    "r2_need_both":  {LANG_ZH: "Remote 2：名稱與本地路徑都必須填寫（或全部留空以清除設定）",
                       LANG_EN: "Remote 2: both name and local path are required (or leave all empty to clear)"},
    "r2_name_conflict": {LANG_ZH: "Remote 2：名稱不可與 Remote 1 相同（'{name}'）",
                          LANG_EN: "Remote 2: name cannot be the same as Remote 1 ('{name}')"},
    "r2_not_repo":   {LANG_ZH: "Remote 2：'{path}' 不是有效的 git repository\n請先在該資料夾執行 git init 或 git clone",
                       LANG_EN: "Remote 2: '{path}' is not a valid git repository\nPlease run git init or git clone in that folder first"},
    "r2_saved":      {LANG_ZH: "Remote 2（'{name}'）：名稱與本地路徑已儲存", LANG_EN: "Remote 2 ('{name}'): name and local path saved"},
    "r2_url_ok":     {LANG_ZH: "Remote 2 URL：OK", LANG_EN: "Remote 2 URL: OK"},
    "r2_url_fail":   {LANG_ZH: "Remote 2 URL：失敗 - {err}", LANG_EN: "Remote 2 URL: failed - {err}"},
    "r2_global_change_cancelled": {LANG_ZH: "Remote 2：已取消變更（保留原有全域設定）",
                                    LANG_EN: "Remote 2: change cancelled (existing global settings kept)"},

    # Push dialog
    "target": {LANG_ZH: "目標", LANG_EN: "Target"},
    "changed_files": {LANG_ZH: "變更的檔案：", LANG_EN: "Changed files:"},
    "no_changes_push": {LANG_ZH: "（沒有變更 — 將推送現有的 commit）", LANG_EN: "(No changes — will push existing commits)"},
    "btn_push_submit": {LANG_ZH: "推送 ↑", LANG_EN: "Push ↑"},
    "btn_pull_submit": {LANG_ZH: "拉取 ↓", LANG_EN: "Pull ↓"},
    "clear": {LANG_ZH: "清除", LANG_EN: "Clear"},
    "clear_confirm_title": {LANG_ZH: "確認清除", LANG_EN: "Confirm Clear"},
    "clear_confirm_msg": {LANG_ZH: "確定要清除已輸入的 Commit 訊息嗎？此動作無法復原。",
                           LANG_EN: "Are you sure you want to clear the commit message? This cannot be undone."},

    "quick_update_schematic": {LANG_ZH: "更新電路圖",     LANG_EN: "Update schematic"},
    "quick_update_pcb":       {LANG_ZH: "更新 PCB 佈局", LANG_EN: "Update PCB layout"},
    "quick_add_component":    {LANG_ZH: "新增元件",       LANG_EN: "Add component"},
    "quick_fix_drc":          {LANG_ZH: "修正 DRC 錯誤",  LANG_EN: "Fix DRC errors"},

    "quick_lib_add":    {LANG_ZH: "新增 ", LANG_EN: "Add "},
    "quick_lib_modify": {LANG_ZH: "修改 ", LANG_EN: "Modify "},
    "quick_lib_remove": {LANG_ZH: "刪除 ", LANG_EN: "Remove "},
    "quick_lib_update": {LANG_ZH: "更新 ", LANG_EN: "Update "},

    "commit_message_project": {LANG_ZH: "專案 Commit 訊息：", LANG_EN: "Project commit message:"},
    "commit_message_library": {LANG_ZH: "元件庫 Commit 訊息：", LANG_EN: "Library commit message:"},

    # Pull dialog
    "pull_warning": {LANG_ZH: "要從遠端拉取最新變更嗎？\n\n⚠  拉取前請先儲存你的工作。",
                      LANG_EN: "Pull latest changes from remote?\n\n⚠  Save your work before pulling."},

    # Operation logs
    "log_gitignore_created":  {LANG_ZH: "▶ 未偵測到 .gitignore，已自動建立", LANG_EN: "▶ No .gitignore found — created automatically"},
    "log_gitignore_updated":  {LANG_ZH: "▶ 已更新 .gitignore（補上缺少的排除項目）", LANG_EN: "▶ Updated .gitignore with missing entries"},
    "log_gitignore_failed":   {LANG_ZH: "⚠  建立 .gitignore 失敗：{err}", LANG_EN: "⚠  Failed to create .gitignore: {err}"},
    "log_untracked_history":  {LANG_ZH: "▶ 已將 .history 從 git 追蹤中移除（已加入 .gitignore）", LANG_EN: "▶ Removed .history from git tracking (added to .gitignore)"},
    "log_staging":            {LANG_ZH: "▶ 正在加入所有變更...", LANG_EN: "▶ Staging all changes..."},
    "log_committing":         {LANG_ZH: "▶ 正在提交：\"{msg}\"", LANG_EN: "▶ Committing: \"{msg}\""},
    "log_nothing_to_commit":  {LANG_ZH: "  （沒有新變更 — 仍繼續推送）", LANG_EN: "  (Nothing new to commit — pushing anyway)"},
    "log_commit_failed":      {LANG_ZH: "\n✗  提交失敗：{err}", LANG_EN: "\n✗  Commit failed: {err}"},
    "log_pushing":            {LANG_ZH: "▶ 正在推送到遠端...", LANG_EN: "▶ Pushing to remote..."},
    "log_push_failed":        {LANG_ZH: "\n✗  推送失敗：{err}", LANG_EN: "\n✗  Push failed: {err}"},
    "log_push_done":          {LANG_ZH: "\n✓  推送完成！", LANG_EN: "\n✓  Push complete!"},

    "log_checking_status":    {LANG_ZH: "▶ 正在檢查本地狀態...", LANG_EN: "▶ Checking local status..."},
    "log_uncommitted":        {LANG_ZH: "⚠  偵測到尚未提交的本地變更：", LANG_EN: "⚠  Uncommitted changes detected:"},
    "log_pull_cancel_keep":   {LANG_ZH: "\n✗  Pull 已取消（保留本地變更，請自行處理後再試）。",
                                LANG_EN: "\n✗  Pull cancelled (local changes kept — please resolve manually and retry)."},
    "log_running_pull":       {LANG_ZH: "▶ 正在執行 git pull...", LANG_EN: "▶ Running git pull..."},
    "log_pull_done":          {LANG_ZH: "\n✓  Pull 完成！", LANG_EN: "\n✓  Pull complete!"},
    "log_reload_hint":        {LANG_ZH: "\n⚠  請關閉並重新開啟專案以載入更新後的檔案。",
                                LANG_EN: "\n⚠  Close and reopen the project to reload updated files."},

    "log_non_ff":             {LANG_ZH: "\n✗  Pull 被拒絕：本地落後遠端 (non-fast-forward)\n{combined}",
                                LANG_EN: "\n✗  Pull rejected: local branch is behind remote (non-fast-forward)\n{combined}"},
    "log_pull_cancel_retry":  {LANG_ZH: "\n✗  Pull 已取消，請自行處理後再試。", LANG_EN: "\n✗  Pull cancelled — please resolve manually and retry."},
    "log_merge_conflict":     {LANG_ZH: "\n✗  Pull 後發生合併衝突 (merge conflict)\n{combined}",
                                LANG_EN: "\n✗  Merge conflict occurred during pull\n{combined}"},
    "log_conflict_files":     {LANG_ZH: "衝突檔案：", LANG_EN: "Conflicted files:"},
    "log_merge_conflict_cancel": {LANG_ZH: "\n✗  Pull 已取消，合併衝突尚未解決，請手動處理。",
                                   LANG_EN: "\n✗  Pull cancelled — merge conflict unresolved, please resolve manually."},
    "log_pull_failed":        {LANG_ZH: "\n✗  Pull 失敗：\n{combined}", LANG_EN: "\n✗  Pull failed:\n{combined}"},

    "log_merge_abort":   {LANG_ZH: "▶ 正在中止未完成的合併 (git merge --abort) ...", LANG_EN: "▶ Aborting unfinished merge (git merge --abort) ..."},
    "log_discard_local": {LANG_ZH: "▶ 正在捨棄本地變更 (git checkout -- .) ...", LANG_EN: "▶ Discarding local changes (git checkout -- .) ..."},
    "log_discard_failed":{LANG_ZH: "\n✗  捨棄本地變更失敗：\n{err}", LANG_EN: "\n✗  Failed to discard local changes:\n{err}"},
    "log_repulling":     {LANG_ZH: "▶ 重新執行 git pull ...", LANG_EN: "▶ Re-running git pull ..."},
    "log_pull_overwritten": {LANG_ZH: "\n✓  Pull 完成！（本地變更已被覆蓋）", LANG_EN: "\n✓  Pull complete! (local changes overwritten)"},

    # Conflict dialogs
    "conflict_uncommitted_title":   {LANG_ZH: "發現未提交的變更", LANG_EN: "Uncommitted Changes Found"},
    "conflict_uncommitted_summary": {LANG_ZH: "Pull 前偵測到尚未提交的本地變更，直接 Pull 可能會失敗或造成衝突。",
                                      LANG_EN: "Uncommitted local changes were detected before pulling — pulling directly may fail or cause conflicts."},
    "conflict_nonff_title":   {LANG_ZH: "Pull 被拒絕 (Non-Fast-Forward)", LANG_EN: "Pull Rejected (Non-Fast-Forward)"},
    "conflict_nonff_summary": {LANG_ZH: "本地分支落後於遠端，Git 拒絕以非 fast-forward 方式合併。",
                                LANG_EN: "The local branch is behind the remote, and Git refused a non-fast-forward merge."},
    "conflict_merge_title":   {LANG_ZH: "發生合併衝突", LANG_EN: "Merge Conflict"},
    "conflict_merge_summary": {LANG_ZH: "Pull 過程中發生合併衝突。", LANG_EN: "A merge conflict occurred during pull."},
    "conflict_affected_files": {LANG_ZH: "受影響的檔案：", LANG_EN: "Affected files:"},
    "conflict_more_files":     {LANG_ZH: "  ... 以及其他 {n} 個檔案", LANG_EN: "  ... and {n} more file(s)"},
    "conflict_choose":         {LANG_ZH: "請選擇處理方式：", LANG_EN: "Please choose how to proceed:"},
    "conflict_keep_local_desc":      {LANG_ZH: "• 保留本地：取消 Pull，不做任何變更，請自行處理",
                                       LANG_EN: "• Keep Local: cancel pull, make no changes — resolve manually"},
    "conflict_overwrite_local_desc": {LANG_ZH: "• 覆蓋本地：捨棄本地變更並以遠端版本覆蓋",
                                       LANG_EN: "• Overwrite Local: discard local changes and overwrite with the remote version"},
    "btn_overwrite_local": {LANG_ZH: "覆蓋本地", LANG_EN: "Overwrite Local"},
    "btn_keep_local":      {LANG_ZH: "保留本地", LANG_EN: "Keep Local"},

    # Status
    "status_fetching":     {LANG_ZH: "▶ 正在取得 git 資訊... ({name})\n", LANG_EN: "▶ Fetching git info... ({name})\n"},
    "status_not_repo":     {LANG_ZH: "✗  '{path}' 不是有效的 git repository", LANG_EN: "✗  '{path}' is not a valid git repository"},
    "status_path":         {LANG_ZH: "路徑：    {path}", LANG_EN: "Path:    {path}"},
    "status_branch":       {LANG_ZH: "分支：    {branch}", LANG_EN: "Branch:  {branch}"},
    "status_remote":       {LANG_ZH: "Remote： {url}", LANG_EN: "Remote:  {url}"},
    "status_no_remote":    {LANG_ZH: "(無)", LANG_EN: "(no remote)"},
    "status_sync":         {LANG_ZH: "同步：    {info}", LANG_EN: "Sync:    {info}"},
    "status_uncommitted":  {LANG_ZH: "尚未提交的變更：", LANG_EN: "Uncommitted changes:"},
    "status_clean":        {LANG_ZH: "✓  工作目錄乾淨", LANG_EN: "✓  Working tree clean"},
    "status_recent_commits": {LANG_ZH: "最近的 Commit：", LANG_EN: "Recent commits:"},

    # Main dialog / misc
    "not_git_repo":      {LANG_ZH: "此專案不在 Git repository 內。\n\n路徑：{path}",
                           LANG_EN: "This project is not inside a Git repository.\n\nPath: {path}"},
    "no_git_action":     {LANG_ZH: "此資料夾尚未初始化為 Git 倉庫。\n\n請先在終端機執行 git init，或至 ⚙ 設定確認路徑後重試。\n\n路徑：{path}",
                           LANG_EN: "This folder is not a Git repository yet.\n\nRun 'git init' in a terminal first, or check the path in ⚙ Settings.\n\nPath: {path}"},
    "commit_msg_empty":  {LANG_ZH: "Commit 訊息不可為空。", LANG_EN: "Commit message cannot be empty."},

    # Update check
    "update_available_title": {LANG_ZH: "發現新版本", LANG_EN: "Update Available"},
    "update_available_msg": {
        LANG_ZH: "目前版本：v{current}\n最新版本：{latest}\n\n以下為最新版本的 README 內容：",
        LANG_EN: "Current version: v{current}\nLatest version: {latest}\n\nLatest README:",
    },
    "btn_update_open":  {LANG_ZH: "更新（開啟瀏覽器）", LANG_EN: "Update (Open Browser)"},
    "btn_skip_version": {LANG_ZH: "跳過此版本", LANG_EN: "Skip This Version"},
}

def t(key, **kwargs):
    lang = get_language()
    entry = STRINGS.get(key)
    if not entry:
        return key
    s = entry.get(lang) or entry.get(LANG_EN) or key
    return s.format(**kwargs) if kwargs else s

def t_en(key, **kwargs):
    """Like t(), but always returns the English string regardless of the
    current language — used for labels that should stay in English
    (main menu, dialog header subtitles)."""
    entry = STRINGS.get(key)
    if not entry:
        return key
    s = entry.get(LANG_EN) or key
    return s.format(**kwargs) if kwargs else s
