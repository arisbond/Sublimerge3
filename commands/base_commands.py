import sublime_plugin
from ..core.window.view.collection import DiffViewCollection
from ..core.window.collection import DiffWindowCollection
from ..core.diff_file import LocalFile, ViewFile

class _BaseCommand(sublime_plugin.WindowCommand):
    _view = None


class _BaseDiffCommand(_BaseCommand):

    def is_context(self):
        self._window = DiffWindowCollection.find(self.window)
        self._view = DiffViewCollection.find(self.window.active_view())
        return self._view not in (None, False)

    def is_allowed_in_dirs_view(self, *args):
        return True

    @staticmethod
    def is_visible_in_menu():
        return False

    def is_dirs_view(self):
        return self._view and self._view.get_view().settings().get("is_sublimerge_dirs_view", False)

    def is_text_view(self):
        return self._view and not self._view.get_view().settings().get("is_sublimerge_dirs_view", False)

    def is_visible(self, *args):
        is_context = self.is_context()
        if not is_context:
            return False
        is_dirs_view = self._view.get_view().settings().get("is_sublimerge_dirs_view", False)
        return not is_dirs_view or self.is_allowed_in_dirs_view(*args)

    def is_enabled(self, *args):
        return self.is_visible(*args)


class _BaseEditorCommand(_BaseCommand):

    def is_context(self):
        return DiffWindowCollection.find(self.window) in (None, False)

    def is_enabled(self, *args):
        return self.is_context()

    def is_visible(self, *args):
        return self.is_enabled(*args)

    @staticmethod
    def is_visible_in_menu():
        return True

    def _get_view(self, index=-1, group=-1, files=[], paths=[]):
        wnd = self.window
        if group == -1 or index == -1:
            return wnd.active_view()
        else:
            views = wnd.views_in_group(group)
            if views is not None and index < len(views):
                return views[index]
            return


class _BaseSidebarCommand(_BaseEditorCommand):

    @staticmethod
    def is_visible_in_true():
        return False

    def _did_select_files(self, files, paths):
        return len(paths) == 2 and len(files) == 2

    def _did_select_dirs(self, files, paths):
        return len(paths) == 2 and len(files) == 0

    def _did_select_comparable(self, files, paths):
        return self._did_select_files(files, paths) or self._did_select_dirs(files, paths)
