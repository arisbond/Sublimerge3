import sublime

class PromiseProgress:

    def __init__(self, promise, message):
        self.promise = promise
        self.promise.then(self._clear).otherwise(self._clear)
        self.msg = message
        self.add = 1
        self.size = 8
        self.speed = 50
        sublime.set_timeout_async((lambda : self.run(0)), self.speed)

    def run(self, i):
        try:
            if not self.promise or self.promise.is_rejected() or self.promise.is_resolved():
                self._clear()
                return
            before = i % self.size
            after = self.size - 1 - before
            for view in sublime.active_window().views():
                view.set_status("000000000000_sm_status", "[%s=%s] %s" % (" " * before, " " * after, self.msg))

            if not after:
                self.add = -1
            if not before:
                self.add = 1
            i += self.add
        except Exception as e:
            print(e)

        sublime.set_timeout_async((lambda : self.run(i)), self.speed)

    def _clear(self, *args):
        self.promise = None
        for view in sublime.active_window().views():
            view.set_status("000000000000_sm_status", " ")
            view.erase_status("000000000000_sm_status")

        return
