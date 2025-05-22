import sublime
from time import sleep
from .debug import console
from .object import Object

class TaskManager:

    def __init__(self, delay=0, is_async=True):
        self._tasks = []
        self._running = None
        self._delay = delay
        self._async = is_async
        self._destroyed = False
        return

    def destroy(self):
        if self._destroyed:
            return
        Object.free(self)

    def add(self, callback, args=[]):
        self._tasks.append(callback)
        self._run()

    def remove(self, callback):
        try:
            self._tasks.remove(callback)
        except:
            pass

    def _run(self):
        if self._running is None:
            self._shift_and_run()
        return

    def _shift_and_run(self):
        try:
            self._running = self._tasks.pop(0)
        except:
            self._running = None
            return

        def inner():
            try:
                self._running()
            except Exception as e:
                console.error("Exception thrown while running task: ", e)

            self._shift_and_run()

        if self._async:
            sublime.set_timeout_async(inner, self._delay)
        else:
            sublime.set_timeout(inner, self._delay)
        return
