import sublime
from ..object import Object
from ..observable import Observable

class Line(Observable):
    TYPE_MISSING = "?"
    TYPE_CHANGE = "."
    TYPE_INSERTED = "+"
    TYPE_REMOVED = "-"
    TYPE_EQUAL = "="
    TYPE_CONFLICT = "!"
    EVENTS = [
     "destroy"]
    _NUM = 0
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, owning_lines, lineno, change_type=TYPE_CHANGE):
        if Object.DEBUG:
            Object.add(self)
        Observable.__init__(self)
        self._type = self.TYPE_EQUAL
        self._name = "line-%d" % Line._NUM
        self._lineno = lineno
        self._owning_lines = owning_lines
        self._view = owning_lines.get_view().get_view()
        self._change_type = change_type
        self._destroyed = False
        Line._NUM += 1

    def __int__(self):
        return self.get_pointer().begin()

    def is_missing(self):
        return self._type == self.TYPE_MISSING

    def is_change(self):
        return self._type == self.TYPE_CHANGE

    def is_inserted(self):
        return self._type == self.TYPE_INSERTED

    def is_removed(self):
        return self._type == self.TYPE_REMOVED

    def is_equal(self):
        return self._type == self.TYPE_EQUAL

    def is_conflict(self):
        return self._change_type == self.TYPE_CONFLICT

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        self._view.erase_regions(self._name)
        self.fire("destroy")
        self.un()
        Object.free(self)

    def is_in_viewport(self):
        if self.is_destroyed():
            return False
        pointer = self.get_pointer().begin()
        viewport = self._view.visible_region()
        return pointer >= viewport.begin() and pointer <= viewport.end()

    def is_destroyed(self):
        return self._destroyed

    def set_type(self, new_type):
        if new_type != self._type:
            self._view.erase_regions(self._name)
        self._type = new_type
        if new_type == self.TYPE_MISSING:
            region = self.get_region()
            if not region.empty():
                self.set_view_text("")

    def get_type(self):
        return self._type

    def get_change_type(self):
        return self._change_type

    def set_change_type(self, change_type):
        self._change_type = change_type

    def get_name(self):
        return self._name

    def get_pointer(self):
        point = self._view.text_point(self._lineno, 0)
        return sublime.Region(point, point)

    def get_region(self):
        return self._view.full_line(self.get_pointer())

    def get_lineno(self):
        return self._lineno

    def set_lineno(self, lineno):
        self._lineno = lineno

    def get_view(self):
        return self._view

    def get_view_text(self):
        return self._view.substr(self._view.line(self.get_pointer()))

    def set_view_text(self, text):
        region = self.get_region()
        if self._owning_lines:
            self._owning_lines.get_view().set_silent("modified", True)
        self._view.run_command("sublimerge_view_replace", {"begin": (region.begin()), 
         "end": (region.end() - 1), 
         "text": text})
        if self._owning_lines:
            self._owning_lines.get_view().set_silent("modified", False)

    def get_owning_lines(self):
        return self._owning_lines
