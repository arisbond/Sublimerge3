import sublime, threading, gc
from ..observable import Observable
from ..debug import console
from ..promise import Promise
from ..startup_restore import StartupRestore
from ..settings import Settings
from .view.diff_view import DiffView
from .collection import DiffWindowCollection
from .alive_checker import DiffWindowAliveChecker
from .layout import DiffWindowLayoutSplitted
from ..object import Object

class BaseWindow(Observable):
    EVENTS = [
     "destroy", "diff_done", "diff_start"]
    WINDOW_MODE_NEW = "@new"
    WINDOW_MODE_CURRENT = "@current"

    @classmethod
    def spawn(self, *args):
        promise = Promise()
        threading.Thread(target=(lambda : self(promise, *args))).start()
        return promise

    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, close_promise, window_mode):
        if Object.DEBUG:
            Object.add(self)
        console.reset_timer()
        console.timer_begin("BaseWindow construction")
        Observable.__init__(self)
        self._window_mode = window_mode
        self._close_promise = close_promise
        self._close_promise.otherwise(self.destroy)
        self._opener = None
        if self._window_mode == self.WINDOW_MODE_NEW:
            if self._can_use_current_window():
                self.DiffWindowLayoutClass = DiffWindowLayoutSplitted
            else:
                self._opener = sublime.active_window()
                sublime.run_command("new_window")
        elif self._window_mode == self.WINDOW_MODE_CURRENT:
            self._original_layout = sublime.active_window().get_layout()
        self._window = sublime.active_window()
        StartupRestore.register_window(self._window, self._opener)
        self._views = []
        self._destroyed = False
        self._layout = None
        self._layout = self.DiffWindowLayoutClass(self)
        self._alive_checker = DiffWindowAliveChecker(self)
        self._selection_modified_promise = None
        self._layout.on("destroy", (lambda sender: self.destroy()))
        self._layout.on("swap", (lambda sender: self._on_swap()))
        DiffWindowCollection.add(self)
        console.timer_end()
        return

    def destroy(self, close_window=True):
        if self._destroyed:
            return
        StartupRestore.unregister_window(self._window, self._opener)
        if self._can_use_current_window():
            close_window = False
        self._destroyed = True
        self.fire("destroy")
        self.un()
        for view in self._views:
            view.destroy()

        self._alive_checker.destroy()
        self._layout.destroy()
        DiffWindowCollection.remove(self)
        self._close_promise.resolve()
        if close_window:

            def close_delayed():
                try:
                    if self._window in sublime.windows():
                        self._window.run_command("close_window")
                        if self._opener:
                            self._opener.run_command("show_overlay", {"overlay": "goto"})
                            self._opener.run_command("hide_overlay")
                            self._opener = None
                            Object.free(self)
                    sublime.set_timeout(gc.collect, 1000)
                except:
                    pass

                return

            sublime.set_timeout(close_delayed, 10)
            sublime.set_timeout(Object.dump, 1500)
        else:
            Object.free(self)

    def can_close(self):
        return True

    def save(self):
        pass

    def get_focused_view(self):
        return self._layout.get_focused_view()

    def add_view(self, view, group=None):
        diff_view = DiffView(self, view=view)
        self._add_diff_view(diff_view, group)
        return diff_view

    def get_window(self):
        return self._window

    def get_views(self):
        return self._views

    def get_layout(self):
        return self._layout

    def get_active_views(self):
        return self._layout.get_active_views()

    def _can_use_current_window(self):
        return Settings.get("use_current_window")

    def _add_diff_view(self, diff_view, group):
        self._views.append(diff_view)
        self._layout.add_view(diff_view, group)
        diff_view.on("selection_modified", self._on_selection_modified)

    def _set_status(self, key, value):
        key = "0000000000aaaaaaa_sm_" + key
        for diff_view in self._layout.get_active_views():
            if value:
                diff_view.get_view().set_status(key, value)
            else:
                diff_view.get_view().erase_status(key)

    def _on_view_load(self, diff_view):
        pass

    def _on_selection_modified(self, diff_view, scroll_to=True):
        pass

    def _on_swap(self):
        pass

    def refresh(self):
        pass

    def on_show_panel(self, panel):
        pass

    def on_hide_panel(self):
        pass
