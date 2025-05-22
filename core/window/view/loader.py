import sublime
from ...diff_file import LocalFile
from ...promise import Promise
from ...debug import console
from ...object import Object

class DiffViewLoader:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self):
        if Object.DEBUG:
            Object.add(self)
        self._load_promise = Promise()
        self._view = None
        return

    def destroy(self):
        Object.free(self)

    def load(self, diff_file, diff_window, view):
        if view is not None:
            self._view = view
            view.set_scratch(True)
            self._check_has_finished_loading()
        else:
            text = diff_file.get_text().replace(diff_file.get_crlf(), "\n") if diff_file else "\n"
            if diff_file.get_path():
                self._view = view = diff_window.get_window().open_file(diff_file.get_path())
                view.set_scratch(True)
                self._check_is_loaded_file(text)
            else:
                self._view = view = diff_window.get_window().new_file()
                view.set_scratch(True)
                view.run_command("sublimerge_view_insert", {"begin": 0, 
                 "text": text})
                sublime.set_timeout(self._load_promise.resolve, 100)
        return (
         view, diff_file, self._load_promise)

    def _check_has_finished_loading(self):
        if self._view.is_loading():
            sublime.set_timeout(self._check_has_finished_loading, 100)
            return
        self._load_promise.resolve()

    def _check_is_loaded_file(self, text):
        if self._view.is_loading():
            sublime.set_timeout((lambda : self._check_is_loaded_file(text)), 100)
            return
        self._view.sel().clear()
        self._view.run_command("sublimerge_view_replace", {"begin": 0, 
         "end": (self._view.size()), 
         "text": text})
        self._load_promise.resolve()
