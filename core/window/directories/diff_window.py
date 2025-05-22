import sublime, os
from ...metadata import PROJECT_NAME
from ...task import Task
from ...debug import console
from ..layout import DiffWindowLayoutDirectories
from ..base_window import BaseWindow
from ..view.diff_view import DiffView
from .listing import Listing
from .behaviors.navigation import NavigationBehavior
from .behaviors.compare import CompareBehavior
from .behaviors.copying import CopyingBehavior

class DiffWindowDirectories(BaseWindow, NavigationBehavior, CompareBehavior, CopyingBehavior):
    DiffWindowLayoutClass = DiffWindowLayoutDirectories

    def __init__(self, close_promise, left_path, right_path, window_mode=BaseWindow.WINDOW_MODE_NEW):
        BaseWindow.__init__(self, close_promise, window_mode)
        NavigationBehavior.__init__(self)
        CompareBehavior.__init__(self)
        CopyingBehavior.__init__(self)
        try:
            self._window.set_sidebar_visible(False)
            self._window.set_minimap_visible(False)
        except Exception as e:
            pass

        self._left_path = left_path
        self._right_path = right_path
        self._left_panel = self._create_diff_view(0)
        self._right_panel = self._create_diff_view(1)
        self._left = self._left_panel.get_view()
        self._right = self._right_panel.get_view()
        self._on_resize_in_progress = False
        self._initializing = True
        self._is_processing = False
        self._current_diff = None
        self._swapped = False
        self._listing = Listing(self._left_path, self._right_path, self._left_panel, self._right_panel)
        self._list_dirs()
        self._left_panel.on("resize", self._on_resize)
        self._right_panel.on("resize", self._on_resize)
        self._layout.sync_to_active()
        self._layout.start_sync()
        return

    def _can_use_current_window(self):
        return False

    def _on_swap(self):
        self._swapped = not self._swapped

    def refresh(self):
        console.log("Refreshing diff view")

    def can_close(self):
        return not self._is_processing and not self._initializing

    def _update_status(self, status):
        self._set_status("dirs_info", status)

    def _create_diff_view(self, group):
        view = self._window.new_file()
        view.set_syntax_file("/".join(["Packages", PROJECT_NAME, "syntax", "Sublimerge.tmLanguage"]))
        view.set_scratch(True)
        settings = {"draw_white_space": "none", 
         "show_line_numbers": False, 
         "word_wrap": False, 
         "is_sublimerge_dirs_view": True, 
         "is_sublimerge_view": True}
        diff_view = self.add_view(view, group)
        for setting in settings:
            view.settings().set(setting, settings[setting])

        diff_view.set_read_only(True)
        diff_view.set_modifyable(True)
        diff_view.set_silent("modified", True)
        return diff_view

    def _list_dirs(self):
        self._listing.create().then((lambda *args: self._list_dirs_done()))

    def _list_dirs_done(self):
        self._initializing = False

    def _on_resize(self, sender, visible_region):
        if self._on_resize_in_progress or self._initializing:
            return
        self._on_resize_in_progress = True
        self._listing.display()
        self._on_resize_in_progress = False
        self.select_current_change()

    def _on_selection_modified(self, diff_view):
        diff_view.get_view().sel().add(sublime.Region(0, 0))
        diff_view.get_view().sel().clear()
        return False

    def _find_change_under_caret(self, *args):
        return

    def can_copy_single_line(self, *args):
        return False

    def destroy(self, close_window=True):
        if self._destroyed:
            return
        CompareBehavior.destroy(self)
        self._listing.destroy()
        BaseWindow.destroy(self, close_window)
