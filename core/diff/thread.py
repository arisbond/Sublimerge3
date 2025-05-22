import threading, sublime, inspect, ctypes
from ..observable import Observable
from .diff import Differ2, Differ3
from ..debug import console
from ..object import Object

class DiffThread2(threading.Thread, Observable):
    EVENTS = [
     "change", "done"]
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_view_left, diff_view_right):
        if Object.DEBUG:
            Object.add(self)
        Observable.__init__(self)
        self._diff_view_left = diff_view_left
        self._diff_view_right = diff_view_right
        threading.Thread.__init__(self)

    def destroy(self):
        Object.free(self)

    def run(self):
        differ = Differ2()
        differ.difference(text1=self._diff_view_left.get_text(), text2=self._diff_view_right.get_text(), callback=(lambda seq_number, change_their, change_mine: self.fire("change", seq_number, change_their, change_mine)), callback_done=(lambda : self.fire("done", self._diff_view_left, self._diff_view_right)), their_crlf=self._diff_view_left.get_view().line_endings(), mine_crlf=self._diff_view_right.get_view().line_endings())

    def fire(self, event, *args):
        Observable.fire(self, event, *args)


class DiffThread3(threading.Thread, Observable):
    EVENTS = [
     "change", "done", "merged"]

    def __init__(self, base_file, diff_view_their, diff_view_merged, diff_view_mine):
        Observable.__init__(self)
        self._diff_view_their = diff_view_their
        self._diff_view_mine = diff_view_mine
        self._base_file = base_file
        threading.Thread.__init__(self)

    def destroy(self):
        self._diff_view_their = None
        self._diff_view_mine = None
        self._base_file = None
        return

    def run(self):
        self._merged_text = None
        self._merged_hunks = None

        def on_merged(text, hunks):
            self._merged_text = text
            self._merged_hunks = hunks

        differ = Differ3()
        differ.difference(their=self._diff_view_their.get_text(), base=self._base_file.get_text(), mine=self._diff_view_mine.get_text(), callback=(lambda seq_number, change_their, change_base, change_mine: self.fire("change", seq_number, change_their, change_base, change_mine)), callback_merged=on_merged, callback_done=(lambda : self.fire("done", self._diff_view_their, self._diff_view_mine, self._merged_text, self._merged_hunks)), their_crlf=self._diff_view_their.get_view().line_endings(), base_crlf=self._base_file.get_crlf(), mine_crlf=self._diff_view_mine.get_view().line_endings())
        return

    def fire(self, event, *args):
        Observable.fire(self, event, *args)
