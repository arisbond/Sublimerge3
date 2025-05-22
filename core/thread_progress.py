import sublime

class ThreadProgress:

    def __init__(self, thread, message):
        self.th = thread
        self.msg = message
        self.add = 1
        self.size = 8
        self.speed = 50
        sublime.set_timeout((lambda : self.run(0)), self.speed)

    def run(self, i):
        if not self.th.is_alive():
            for window in sublime.windows():
                for view in window.views():
                    view.erase_status("000000000000_sm_status")

            return
        before = i % self.size
        after = self.size - 1 - before
        for window in sublime.windows():
            for view in window.views():
                view.set_status("000000000000_sm_status", "[%s=%s] %s" % (" " * before, " " * after, self.msg))

        if not after:
            self.add = -1
        if not before:
            self.add = 1
        i += self.add
        sublime.set_timeout((lambda : self.run(i)), self.speed)
