import sublime
from ..object import Object
from ..observable import Observable

class LinesGroup(Observable):
    _NUM = 0
    EVENTS = ["destroy"]
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, owning_lines):
        if Object.DEBUG:
            Object.add(self)
        Observable.__init__(self)
        self._lines = []
        self._name = "group-%d" % LinesGroup._NUM
        self._view = owning_lines.get_view().get_view()
        self._diff_view = owning_lines.get_view()
        self._destroyed = False
        LinesGroup._NUM += 1

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        while self._lines:
            self._lines.pop().un("destroy", self._on_line_destroy)

        self.fire("destroy")
        self.un()
        del self._name
        del self._view
        del self._diff_view

    def add_line(self, line):
        line.un("destroy", self._on_line_destroy)
        line.on("destroy", self._on_line_destroy)
        self._lines.append(line)

    def get_region(self):
        return sublime.Region(self._lines[0].get_region().begin(), self._lines[-1].get_region().end())

    def get_lines(self):
        return self._lines

    def get_name(self):
        return self._name

    def get_view(self):
        return self._view

    def get_view_text(self):
        text = ""
        for line in self._lines:
            if line.is_missing():
                continue
            text += line.get_view_text() + "\n"

        return text

    def _on_line_destroy(self, line):
        self._lines.remove(line)
        if not self._lines:
            self.destroy()
