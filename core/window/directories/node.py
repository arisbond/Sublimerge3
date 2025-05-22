from ...object import Object
from ...observable import Observable
from .item import TYPE_CHANGE, TYPE_REMOVED, TYPE_INSERTED

class Node(Observable):
    EVENTS = [
     "destroy"]

    def __init__(self, left, right, left_path, right_path, diffs, row, max_len):
        self.left = left
        self.right = right
        self.listing = None
        self.diffs = diffs
        self.left_path = left_path
        self.right_path = right_path
        self._selected = False
        self._row = row
        self._max_len = max_len
        return

    def __repr__(self):
        return "Node: %s" % self.get_name()

    def destroy(self):
        self.fire("destroy")
        self.clear()
        self.un()
        self.left.destroy()
        self.right.destroy()
        Object.free(self)

    def is_dir(self):
        return (self.left.is_dir or self.left.is_missing()) and (self.right.is_dir or self.right.is_missing())

    def has_missing(self):
        return self.left.is_missing() or self.right.is_missing()

    def get_name(self):
        return self.left.name or self.right.name

    def get_row(self):
        return self.left.get_row() or self.right.get_row()

    def set_row(self, row):
        self._row = row
        self.left.set_row(row)
        self.right.set_row(row)

    def select(self):
        self._selected = True
        self.left.select()
        self.right.select()

    def unselect(self):
        self._selected = False
        self.left.unselect()
        self.right.unselect()

    def is_selected(self):
        return self._selected

    def render(self):
        self.left.set_row(self._row)
        self.right.set_row(self._row)
        return (
         self.left.render(self._max_len), self.right.render(self._max_len))

    def clear(self):
        self.left.clear()
        self.right.clear()

    def is_equal(self):
        return self.left.get_type() is None and self.right.get_type() is None

    def set_type(self, type):
        self.left.set_type(type)
        self.right.set_type(type)

    def mark(self):
        if self.left.is_missing():
            self.left.set_type(TYPE_REMOVED)
            self.right.set_type(TYPE_INSERTED)
        elif self.right.is_missing():
            self.right.set_type(TYPE_REMOVED)
            self.left.set_type(TYPE_INSERTED)
        elif self.diffs > 0:
            self.left.set_type(TYPE_CHANGE)
            self.right.set_type(TYPE_CHANGE)
        else:
            self.left.set_type(None)
            self.right.set_type(None)
        return
