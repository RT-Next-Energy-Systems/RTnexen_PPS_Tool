import pcbnew
import os


class GitMainAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "RTnexen PPS Tool"
        self.category = "RTnexen PPS Tool"
        self.description = "Git Push / Pull / Status — RTnexen PPS Tool"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(
            os.path.dirname(__file__), "icons", "git_main.png"
        )

    def Run(self):
        import wx
        board = pcbnew.GetBoard()
        project_path = os.path.dirname(board.GetFileName())
        from .git_runner import run_main_dialog
        run_main_dialog(project_path)
