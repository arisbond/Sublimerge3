import sublime, os
from .base_commands import _BaseEditorCommand
from ..core.window.text.diff_window import DiffWindow2, DiffWindow3
from ..core.window.directories.diff_window import DiffWindowDirectories
from ..core.menu import Menu, MenuItem
from ..core.utils import get_comparable_views, is_view_comparable, create_tmp_pair, sanitize_title
from ..core.diff_file import ClipboardFile, ViewFile, LocalFile, ViewRegionFile
from ..core.linsp import LInsp
from ..core.settings import Settings
from ..core.utils import error_message, common_path

class SublimergeTestCompareCommand(_BaseEditorCommand):

    def is_visible(self):
        return Settings.get("__devel__")

    def description(self):
        return "Test: Compare"

    def run(self):
        DiffWindow2.spawn(LocalFile(os.path.expanduser("~/Workspace/Test Data/test 1/their-bak.txt")), LocalFile(os.path.expanduser("~/Workspace/Test Data/test 1/mine-bak.txt")))


class SublimergeTestMergeCommand(_BaseEditorCommand):

    def is_visible(self):
        return Settings.get("__devel__")

    def description(self):
        return "Test: Merge"

    def run(self):
        DiffWindow3.spawn(LocalFile(os.path.expanduser("~/Workspace/Test Data/test 1/their-bak.txt"), read_only=True), LocalFile(os.path.expanduser("~/Workspace/Test Data/test 1/base.txt"), read_only=True), LocalFile(os.path.expanduser("~/Workspace/Test Data/test 1/mine-bak.txt"), read_only=True), LocalFile(os.path.expanduser("~/Workspace/Test Data/test 1/merged.txt")))


class SublimergeTestCompareDirectoriesCommand(_BaseEditorCommand):

    @staticmethod
    def is_visible_in_menu():
        return Settings.get("__devel__")

    def description(self, index=-1, group=-1):
        return "Test: Directories"

    def run(self, index=-1, group=-1):
        DiffWindowDirectories.spawn(os.path.expanduser("~/Workspace/Test Data/a"), os.path.expanduser("~/Workspace/Test Data/b"))


class SublimergeCompareToViewCommand(_BaseEditorCommand):
    _views = None

    def description(self, index=-1, group=-1):
        if self._views and len(self._views) == 1:
            return "Compare to %s" % self._views[0][0][0]
        return "Compare to View..."

    def run(self, index=-1, group=-1):
        active_view = self._get_view(index, group)

        def spawn(view_a, view_b):
            dir_name = create_tmp_pair(view_a.file_name() or sanitize_title(view_a.name()), view_b.file_name() or sanitize_title(view_b.name()))
            DiffWindow2.spawn(ViewFile(view=view_a, path=dir_name[0]), ViewFile(view=view_b, path=dir_name[1]))

        if len(self._views) == 1:
            spawn(self._views[0][1], active_view)
        else:
            menu = Menu(items=[MenuItem(caption=view[0], value=view[1]) for view in self._views], on_select=(lambda sender, item: (
             spawn(item.get_value(), active_view),
             sender.destroy())), on_cancel=(lambda sender: sender.destroy()))
            menu.show()

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        if not is_view_comparable(view):
            return False
        self._views = get_comparable_views(view)
        return not not (_BaseEditorCommand.is_visible(self) and self._views and len(self._views) > 0)


class SublimergeCompareToClipboardCommand(_BaseEditorCommand):

    def description(self, index=-1, group=-1):
        return "Compare to Clipboard"

    def run(self, index=-1, group=-1):
        active_view = self._get_view(index, group)
        DiffWindow2.spawn(ClipboardFile(), ViewFile(active_view))

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        if not is_view_comparable(view):
            return False
        return not not (_BaseEditorCommand.is_visible(self) and bool(sublime.get_clipboard()))


class SublimergeCompareSelectedLinesCommand(_BaseEditorCommand):

    def description(self, index=-1, group=-1):
        return "Compare Selected Lines"

    def run(self, index=-1, group=-1):
        active_view = self._get_view(index, group)
        DiffWindow2.spawn(ViewRegionFile(view=active_view, region=active_view.sel()[0]), ViewRegionFile(view=active_view, region=active_view.sel()[1]))

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        if not is_view_comparable(view):
            return False
        return not not (_BaseEditorCommand.is_visible(self) and len(view.sel()) == 2)


class SublimergeCompareSelectedLinesInViewsCommand(_BaseEditorCommand):

    def description(self, index=-1, group=-1):
        return "Compare Selected Lines in Views"

    def run(self, index=-1, group=-1):
        active_view = self._get_view(index, group)

        def num_sel_lines(view):
            n = len(view.lines(view.sel()[0]))
            return (n, "" if n == 1 else "s")

        def spawn(view_a, view_b):
            DiffWindow2.spawn(ViewRegionFile(view=view_a, region=view_a.sel()[0]), ViewRegionFile(view=view_b, region=view_b.sel()[0]))

        menu = Menu(items=[MenuItem(caption=view[0] + ["%d line%s selected" % num_sel_lines(view[1])], value=view[1]) for view in self._views], on_select=(lambda sender, item: (
         spawn(item.get_value(), active_view),
         sender.destroy())), on_cancel=(lambda sender: sender.destroy()))
        menu.show()

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        if not is_view_comparable(view):
            return False
        self._views = get_comparable_views(view)
        return not not (_BaseEditorCommand.is_visible(self) and self._views and len(self._views) > 0)


class SublimergeCompareSelectedLinesToClipboardCommand(_BaseEditorCommand):

    def description(self, index=-1, group=-1):
        return "Compare Selected Lines to Clipboard"

    def run(self, index=-1, group=-1):
        view = self._get_view(index, group)
        DiffWindow2.spawn(ClipboardFile(), ViewRegionFile(view=view, region=view.sel()[0]))

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        if not is_view_comparable(view):
            return False
        return not not (_BaseEditorCommand.is_visible(self) and len(view.sel()) > 0)


class SublimergeShowUnsavedChangesCommand(_BaseEditorCommand):

    def description(self, index=-1, group=-1):
        return "Show Unsaved Changes"

    def run(self, index=-1, group=-1):
        view = self._get_view(index, group)
        DiffWindow2.spawn(LocalFile(path=view.file_name()), ViewFile(view=view, title="~ %s" % os.path.basename(view.file_name())))

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        if not is_view_comparable(view):
            return False
        return not not (_BaseEditorCommand.is_visible(self) and view.is_dirty() and bool(view.file_name()))


class SublimergeNothingToShowCommand(_BaseEditorCommand):

    @staticmethod
    def is_visible_in_menu():
        return False


class SublimergeRegisterCommand(_BaseEditorCommand):

    @staticmethod
    def is_visible_in_menu():
        return False

    def description(self, index=-1, group=-1):
        return "Enter License"

    def is_visible(self, index=-1, group=-1):
        return not LInsp.r_ok()

    def run(self, index=-1, group=-1):
        LInsp.r_pfk()


class SublimergeUnregisterCommand(_BaseEditorCommand):

    @staticmethod
    def is_visible_in_menu():
        return False

    def description(self, index=-1, group=-1):
        return "Remove License"

    def is_visible(self, index=-1, group=-1):
        return LInsp.r_ok()

    def run(self, index=-1, group=-1):
        LInsp.r_uk()


class SublimergeComparePathsCommand(_BaseEditorCommand):

    @staticmethod
    def is_visible_in_menu():
        return False

    def run(self, paths=[]):
        if not os.path.exists(paths[0]):
            error_message("%s: no such file or directory" % paths[0])
            return
        if not os.path.exists(paths[1]):
            error_message("%s: no such file or directory" % paths[1])
            return
        if os.path.isdir(paths[0]) and os.path.isdir(paths[1]):
            if common_path(paths[0], paths[1]) in paths:
                error_message("Can't compare parent and descendant directories")
                return
            else:
                DiffWindowDirectories.spawn(paths[0], paths[1])
                return
        if os.path.isfile(paths[0]) and os.path.isfile(paths[1]):
            DiffWindow2.spawn(LocalFile(paths[0]), LocalFile(paths[1]))
            return
        error_message("Two paths to files or directories must be given.")
