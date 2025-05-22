import sublime
from ..object import Object

class DiffWindowAliveChecker:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_window):
        if Object.DEBUG:
            Object.add(self)
        self._diff_window = diff_window
        self._window = diff_window.get_window()
        self._destroyed = False

    def _check_alive(self):
        if self._destroyed:
            return
        if self._window in sublime.windows():
            sublime.set_timeout(self._check_alive, 100)
        else:
            self.destroy()

    def destroy(self):
        self._destroyed = True
        self._diff_window.destroy(close_window=False)
        self._diff_window = None
        self._window = None
        return
