import sublime, difflib, time, threading, re
from ...utils import random_string, splitlines
from ...promise import Promise
from ...object import Object

class Stack:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self):
        if Object.DEBUG:
            Object.add(self)
        self._undo = []
        self._redo = []
        self._index = -1

    def __len__(self):
        return len(self._undo + self._redo)

    def clear(self):
        self.__init__()

    def push(self, item, overwrite_last=False):
        self._undo.append(item)
        self._redo = []

    def last(self):
        if self._undo:
            return self._undo[-1]
        else:
            return

    def backward(self):
        if self._undo:
            item = self._undo.pop()
            self._redo.append(item)
            return item

    def forward(self):
        if self._redo:
            item = self._redo.pop()
            self._undo.append(item)
            return item

    def dump(self):
        pass


class DiffViewHistory:
    HUNK_RE = re.compile("^@@ \\-(\\d+),?(\\d*) \\+(\\d+),?(\\d*) @@")
    SNAPSHOT_DEFER = 500

    def __init__(self, diff_window):
        self._window = diff_window
        self._views = diff_window.get_layout().get_active_views()
        self._stack = Stack()
        self._running = False
        self._last_text = {}
        self._last_lines = {}
        self._last_selection = {}
        self._diff_zero_offset = self._find_zero_offset()
        self._random_footer = "<<<<<" + random_string(40) + ">>>>>"
        self._snapshot_promise = None
        return

    def _find_zero_offset(self):
        for line in difflib.unified_diff("a\nb\n\\c\n\\d", "a\n\\c\n\\d", n=0):
            hunk = re.match(self.HUNK_RE, line)
            if hunk:
                start_left = int(hunk.group(1)) - 1
                start_right = int(hunk.group(3)) - 1
                size_left = int(hunk.group(2) or 1)
                size_right = int(hunk.group(4) or 1)
                if start_left != start_right:
                    return 1
                continue

        return 0

    def __len__(self):
        return len(self._stack)

    def reset(self):
        self._stack.clear()
        self._last_text = {}
        self._last_lines = {}
        self._last_selection = {}

    def initialize(self):
        for diff_view in self._window.get_active_views():
            v = diff_view.get_view()
            self._last_text.update({(v.id()): (v.substr(sublime.Region(0, v.size())))})
            self._last_lines.update({(v.id()): (diff_view.get_lines().serialize())})
            self._last_selection.update({(v.id()): [sel for sel in v.sel()]})

    def initialize_selection(self):
        for diff_view in self._window.get_active_views():
            v = diff_view.get_view()
            if v.id() not in self._last_text or v.substr(sublime.Region(0, v.size())) != self._last_text[v.id()]:
                return

        for diff_view in self._window.get_active_views():
            v = diff_view.get_view()
            self._last_selection.update({(v.id()): [sel for sel in v.sel()]})

    def destroy(self):
        self._window = None
        self._views = None
        return

    def _generate_text_patch(self, diff_view):
        view = diff_view.get_view()
        text = view.substr(sublime.Region(0, view.size()))
        if text == self._last_text:
            return None
        else:
            patch = {"undo": [],  "redo": []}
            if view.id() in self._last_text:
                a = splitlines(text) + ["EOF"]
                b = splitlines(self._last_text[view.id()]) + ["EOF"]
                for line in difflib.unified_diff(a, b, n=0):
                    patch["undo"].append(line)

                for line in difflib.unified_diff(b, a, n=0):
                    patch["redo"].append(line)

            return patch

    def _generate_lines_patch(self, diff_view):
        return {"undo": (self._last_lines[diff_view.get_view().id()]), 
         "redo": (diff_view.get_lines().serialize())}

    def _generate_selection_patch(self, diff_view):
        return {"undo": (self._last_selection[diff_view.get_view().id()]), 
         "redo": [sel for sel in diff_view.get_view().sel()]}

    def snapshot(self):
        if self._snapshot_promise:
            self._snapshot_promise.reject()
        self._snapshot_promise = promise = Promise().then(self._snapshot_task)
        sublime.set_timeout((lambda : promise.resolve()), self.SNAPSHOT_DEFER)

    def _snapshot_task(self):
        item = []
        if not self._window:
            return
        for diff_view in self._window.get_active_views():
            item.append((
             diff_view,
             self._generate_lines_patch(diff_view),
             self._generate_text_patch(diff_view),
             self._generate_selection_patch(diff_view)))
            view = diff_view.get_view()

        if self._stack.last() == item:
            return
        self._stack.push(item)
        self.initialize()

    def undo(self, diff_view):
        if self._running:
            return
        self._force_promise_resolve()
        item = self._stack.backward()
        if item:
            self._running = True
            threading.Thread(target=self.apply(item, "undo")).start()

    def redo(self, diff_view):
        if self._running:
            return
        self._force_promise_resolve()
        item = self._stack.forward()
        if item:
            self._running = True
            threading.Thread(target=self.apply(item, "redo")).start()

    def _force_promise_resolve(self):
        if self._snapshot_promise:
            if not self._snapshot_promise.is_resolved() and not self._snapshot_promise.is_rejected():
                self._snapshot_promise.resolve()

    def apply(self, item, which):
        for entry in item:
            diff_view, serialized_lines, patch, selection = entry
            if len(selection[which]) > 0:
                if not diff_view.get_view().visible_region().contains(selection[which][0]):
                    diff_view.get_view().show_at_center(selection[which][0])
            diff_view.set_silent("modified", True)
            modified_lines = self._apply_patch(diff_view, patch[which])
            diff_view.get_lines().unserialize(serialized_lines[which], modified_lines)
            diff_view.get_view().sel().clear()
            diff_view.get_view().sel().add_all(selection[which])
            diff_view.set_silent("modified", False)

        self.initialize()

        def inner():
            self._running = False

        sublime.set_timeout(inner, 1)

    def _apply_patch(self, diff_view, patch):
        view = diff_view.get_view()
        line_offset = 0
        view_size = view.size()
        view_text = view.substr(sublime.Region(0, view_size))
        view_text = splitlines(view_text)
        hunk = None
        modified_lines = []
        for line in patch:
            if line.startswith("@"):
                match = re.match(self.HUNK_RE, line)
                if hunk is not None:
                    self._apply_hunk(view, hunk)
                start_left = int(match.group(1)) - 1 + line_offset
                start_right = int(match.group(3)) - 1
                size_left = int(match.group(2) or 1)
                size_right = int(match.group(4) or 1)
                if size_left == 0:
                    start_left += self._diff_zero_offset
                if size_right == 0:
                    start_right += self._diff_zero_offset
                hunk = (
                 start_left,
                 size_left,
                 start_right,
                 size_right, {"-": [],  "+": []})
                line_offset += size_right - size_left
                modified_lines.append(start_left)
            elif hunk is not None and line:
                hunk[4][line[0]].append(line[1:])
                continue

        if hunk is not None:
            self._apply_hunk(view, hunk)
        return modified_lines

    def _apply_hunk(self, view, hunk):
        start_left, size_left, start_right, size_right, text = hunk
        if size_left == 0:
            begin = view.text_point(start_left, 0)
            view.run_command("sublimerge_view_insert", {"begin": begin, 
             "text": ("".join(text["+"]))})
        else:
            begin = view.text_point(start_left, 0)
        if size_left > 0:
            end = view.full_line(view.text_point(start_left + size_left - 1, 0)).end()
            view.run_command("sublimerge_view_replace", {"begin": begin, 
             "end": end, 
             "text": ("".join(text["+"]))})
