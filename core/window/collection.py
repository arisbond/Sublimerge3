import sublime

class DiffWindowCollection:
    _diff_windows = []

    @staticmethod
    def add(diff_window):
        DiffWindowCollection._diff_windows.append(diff_window)

    @staticmethod
    def remove(diff_window):
        DiffWindowCollection._diff_windows.remove(diff_window)

    @staticmethod
    def find(sublime_window):
        for diff_window in DiffWindowCollection._diff_windows:
            try:
                if sublime_window.id() == diff_window.get_window().id():
                    if sublime_window.active_view().id() in [v.get_view().id() for v in diff_window.get_views()]:
                        return diff_window
            except:
                pass

        return False

    @staticmethod
    def get_active():
        return DiffWindowCollection.find(sublime.active_window())
