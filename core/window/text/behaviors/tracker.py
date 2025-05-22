import sublime
from ....utils import subtract_regions
from ....observable import Observable
from ....debug import console
from ....object import Object

class Tracker(Observable):
    EVENTS = [
     "modified"]
    MARKER_NUM = 0
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_view):
        if Object.DEBUG:
            Object.add(self)
        self._selected_lines = []
        self._diff_view = diff_view
        self._view = diff_view.get_view()
        self._skip_selection_modified = False
        diff_view.on("selection_modified", self.on_selection_modified)
        diff_view.on("modified", self.on_buffer_modified)
        Observable.__init__(self)

    def destroy(self):
        self._selected_lines = None
        self._diff_view = None
        self._view = None
        self._skip_selection_modified = None
        self.un()
        return

    def on_selection_modified(self, sender, *args):
        if self._skip_selection_modified or not self._diff_view.is_loaded():
            return
        else:
            while self._selected_lines:
                item = self._selected_lines.pop()
                if item[1] is not None:
                    self._view.erase_regions(item[1])
                del item

            sel = self._view.sel()
            if len(sel) == 0:
                return
            _rowcol = self._view.rowcol
            _substr = self._view.substr
            row_begin, col_begin = _rowcol(sel[0].begin())
            row_end, col_end = _rowcol(sel[0].end())
            total_rows = _rowcol(self._view.size())[0]
            if row_begin == total_rows:
                row_begin -= 1
                row_end -= 1
            for lineno in range(row_begin - 1, row_end + 2):
                name = "line-marker-%d" % self.MARKER_NUM
                self.MARKER_NUM += 1
                if lineno == -1 or lineno > total_rows:
                    self._selected_lines.append((None, None, None, None))
                else:
                    point = self._view.text_point(lineno, 0)
                    pointer = sublime.Region(point, point)
                    line = (
                     lineno, name, pointer, _substr(self._view.line(pointer)))
                    self._view.add_regions(name, [pointer], "", "", sublime.HIDDEN)
                    self._selected_lines.append(line)

            return

    def on_buffer_modified(self, sender):
        if not self._diff_view.is_loaded() or not self._selected_lines:
            return
        else:
            self._diff_view.set_silent("selection_modified", True)
            self._skip_selection_modified = True
            previous_pointer = sublime.Region(-1, -1)
            removed = []
            modified = []
            inserted = []
            was_first = False
            cleanup = []
            for lineno, name, pointer, text in self._selected_lines[1:-1]:
                if name is None:
                    continue
                cleanup.append(name)
                moved_pointer = self._view.get_regions(name)[0]
                new_begin = moved_pointer.begin()
                row, col = self._view.rowcol(new_begin)
                if lineno > row:
                    if col > 0:
                        removed.append(lineno)
                    else:
                        removed.append(lineno - 1)
                elif text != self._view.substr(self._view.line(new_begin)):
                    modified.append(lineno)
                previous_pointer = pointer

            first = self._selected_lines[0]
            last = self._selected_lines[-1]
            if first[0] is None:
                begin = 0
            else:
                begin = self._view.full_line(self._view.get_regions(first[1])[0]).end()
            if last[0] is None:
                end = self._view.size()
            else:
                end = self._view.full_line(self._view.get_regions(last[1])[0]).begin()
            added_regions = subtract_regions(sublime.Region(begin, end), [self._view.full_line(self._view.get_regions(line[1])[0]) for line in self._selected_lines if line[0] is not None])
            for added in added_regions:
                added_lines = self._view.split_by_newlines(added)
                for line_region in added_lines:
                    lineno = self._view.rowcol(line_region.begin())[0]
                    inserted.append(lineno)

            if not modified:
                if not removed and not inserted:
                    modified = [
                     self._view.rowcol(self._view.size())[0]]
            modified = [v for v in modified if v not in removed]
            inserted = [v for v in inserted if v not in modified]
            for v in cleanup:
                self._view.erase_regions(v)

            self.fire("modified", modified, removed, inserted)
            self._skip_selection_modified = False
            self._diff_view.set_silent("selection_modified", False)
            self._diff_view.fire("selection_modified")
            return
