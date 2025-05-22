import sublime, json
from os.path import exists
from .utils import fopen
IS_SUBLIMERGE_WINDOW_KEY = "__is_sublimerge_window__"
PROJECT_TO_RESTORE_KEY = "__project_to_restore__"
LAYOUT_TO_RESTORE_KEY = "__layout_to_restore__"
IS_SIDEBAR_VISIBLE_KEY = "__is_sidebar_visible__"

class StartupRestore:

    @classmethod
    def save_current_layout(self):
        pass

    @classmethod
    def initialize(self):
        sublimerge_windows = [w for w in sublime.windows() if w.settings().get(IS_SUBLIMERGE_WINDOW_KEY)]
        sublime_windows = [w for w in sublime.windows() if not w.settings().get(IS_SUBLIMERGE_WINDOW_KEY)]
        project_to_restore = None
        window_to_restore_project = None
        if len(sublime_windows) == 0:
            sublime.run_command("new_window")
            window_to_restore_project = sublime.active_window()
        for w in sublimerge_windows:
            project_to_restore = project_to_restore if project_to_restore else w.settings().get(PROJECT_TO_RESTORE_KEY)
            w.settings().erase(IS_SUBLIMERGE_WINDOW_KEY)
            w.settings().erase(PROJECT_TO_RESTORE_KEY)
            if w.settings().has(LAYOUT_TO_RESTORE_KEY):
                for view in w.views():
                    if view.settings().get("is_sublimerge_view"):
                        view.close()
                        continue

                w.set_layout(w.settings().get(LAYOUT_TO_RESTORE_KEY))
                window_to_restore_project = w
                w.set_sidebar_visible(bool(w.settings().get(IS_SIDEBAR_VISIBLE_KEY)))
            else:
                w.run_command("close_window")

        if window_to_restore_project:
            if project_to_restore and exists(project_to_restore):
                try:
                    f = fopen(project_to_restore, "r")
                    data = json.load(f)
                    f.close()
                    window_to_restore_project.set_project_data(data)
                except:
                    pass

        return

    @classmethod
    def register_window(self, window, opener):
        window.settings().set(IS_SUBLIMERGE_WINDOW_KEY, True)
        if opener:
            window.settings().set(PROJECT_TO_RESTORE_KEY, opener.project_file_name())

    @classmethod
    def unregister_window(self, window, opener):
        window.settings().erase(IS_SUBLIMERGE_WINDOW_KEY)
        if opener:
            window.settings().erase(PROJECT_TO_RESTORE_KEY)
