import sublime
from time import sleep
from ....utils import prepare_to_compare, splitlines
from ....lines.line import Line
from .diff_live_base import DiffLiveBase

class BehaviorWindowDiffLive2(DiffLiveBase):

    def modified(self, diff_view, modified, removed, inserted):
        if not removed and not inserted and modified:
            self._on_line_modified(diff_view, modified[0])
        elif removed:
            if modified:
                lines = diff_view.get_lines()
                other_view = self._other(diff_view)
                other_lines = other_view.get_lines()
                for lineno in removed:
                    lines.get_line(lineno)
                    other_line = other_lines.get_line(lineno)
                    lines.removed_line_by_user(lineno)
                    lines.create_empty_line(lineno)
                    self._set_line_type(diff_view, lineno, Line.TYPE_MISSING)

                self._on_line_modified(diff_view, modified[0])
        self._apply()

    def insert(self, diff_view):
        sel_begin = self._selection_begin(diff_view)
        sel_end = self._selection_end(diff_view)
        if not sel_begin:
            return False
        if sel_begin != sel_end:
            return True
        row, col = sel_begin
        line = diff_view.get_lines().get_line(row)
        next_line = diff_view.get_lines().get_line(row + 1)

        def is_caret_at_line_begin():
            return col == 0

        def is_caret_at_line_end():
            return col == line.get_region().size() - 1

        def is_caret_at_line_middle():
            return col > 0 and col < line.get_region().size() - 1

        def is_line_with_caret_empty():
            return line.get_region().size() == 1

        other_view = self._other(diff_view)
        other_lines = other_view.get_lines()
        if line.is_missing():
            self._set_line_type(diff_view, row, Line.TYPE_EQUAL)
            self._on_line_modified(diff_view, row)
            self._apply()
            return False
        if next_line.is_missing() and (is_caret_at_line_end() or is_line_with_caret_empty()):
            self._set_line_type(diff_view, row + 1, Line.TYPE_EQUAL)
            self._on_line_modified(diff_view, row + 1)
            self._move_caret_to_line_end(diff_view, row + 1)
            self._apply()
            return False
        if is_caret_at_line_begin():
            other_lines.create_empty_line(row)
            diff_view.get_lines().create_empty_line(row)
            self._move_caret_to_line_begin(diff_view, row + 1)
            self._set_line_type(diff_view, row, Line.TYPE_INSERTED)
            self._apply()
            return False
        if is_caret_at_line_end():
            other_lines.create_empty_line(row + 1)
            diff_view.get_lines().create_empty_line(row + 1)
            self._move_caret_to_line_begin(diff_view, row + 1)
            self._set_line_type(diff_view, row + 1, Line.TYPE_INSERTED)
            self._apply()
            return False
        if is_caret_at_line_middle():
            text_left = line.get_view_text()[:col]
            text_right = line.get_view_text()[col:]
            line.set_view_text(text_left)
            self._on_line_modified(diff_view, row)
            other_lines.create_empty_line(row + 1)
            new_line = diff_view.get_lines().create_empty_line(row + 1)
            new_line.set_view_text(text_right)
            self._set_line_type(diff_view, row + 1, Line.TYPE_INSERTED)
            self._move_caret_to_line_begin(diff_view, row + 1)
            self._apply()
            return False
        return True

    def left_delete(self, diff_view):
        sel_begin = self._selection_begin(diff_view)
        sel_end = self._selection_end(diff_view)
        if not not sel_begin:
            if sel_begin == sel_end == (0, 0):
                return False
        if sel_begin != sel_end:
            self._delete_selection(diff_view, sel_begin, sel_end)
            return False
        row, col = sel_begin
        if col > 0:
            return True
        current_line = diff_view.get_lines().get_line(row)
        if current_line.is_missing():
            self._move_caret_before_missings(diff_view, current_line)
            return False
        return self._join_lines_before_missings_left(diff_view, current_line)

    def right_delete(self, diff_view):
        sel_begin = self._selection_begin(diff_view)
        sel_end = self._selection_end(diff_view)
        if not sel_begin:
            return False
        if sel_begin != sel_end:
            self._delete_selection(diff_view, sel_begin, sel_end)
            return False
        row, col = sel_begin
        current_line = diff_view.get_lines().get_line(row)
        if col < current_line.get_region().size() - 1:
            return True
        if current_line.is_missing():
            self._move_caret_after_missings(diff_view, current_line)
            return False
        return self._join_lines_before_missings_right(diff_view, current_line)

    def paste(self, diff_view):
        clipboard_text = sublime.get_clipboard()
        if not clipboard_text:
            return False
        sel_begin = self._selection_begin(diff_view)
        sel_end = self._selection_end(diff_view)
        if sel_begin != sel_end:
            self._delete_selection(diff_view, sel_begin, sel_end)
        lines_to_paste = splitlines(clipboard_text, False)
        lines = diff_view.get_lines()
        other_view = self._other(diff_view)
        other_lines = other_view.get_lines()
        row, col = self._selection_begin(diff_view)
        for i, pasted_line_text in enumerate(lines_to_paste):
            line = lines.get_line(row + i)
            pasted_line_text = pasted_line_text.rstrip("\n\r")
            if i == 0:
                line_text = line.get_view_text()
                text_left = line_text[:col]
                text_right = line_text[col:]
                line.set_view_text(text_left + pasted_line_text)
            elif line.is_missing():
                line.set_view_text(pasted_line_text)
            else:
                line = lines.create_empty_line(row + i)
                other_lines.create_empty_line(row + i)
                self._set_line_type(diff_view, row + i, Line.TYPE_INSERTED)
                line.set_view_text(pasted_line_text)
            if i == len(lines_to_paste) - 1:
                caret_col = len(line.get_view_text())
                line.set_view_text(line.get_view_text() + text_right)
                self._move_caret_to_line_col(diff_view, row + i, caret_col)
            self._on_line_modified(diff_view, row + i)

        self._apply()
        return False

    def _on_line_modified(self, diff_view, lineno):
        other_view = self._other(diff_view)
        modified_line = diff_view.get_lines().get_line(lineno)
        other_line = other_view.get_lines().get_line(lineno)
        if other_line.is_missing():
            self._set_line_type(diff_view, lineno, Line.TYPE_INSERTED)
        elif self._lines_equals(modified_line, other_line):
            self._set_line_type(diff_view, lineno, Line.TYPE_EQUAL)
        else:
            self._set_line_type(diff_view, lineno, Line.TYPE_CHANGE)

    def _remove_line(self, diff_view, lineno):
        other_view = self._other(diff_view)
        line = diff_view.get_lines().get_line(lineno)
        other_line = other_view.get_lines().get_line(lineno)
        if other_line.is_missing():
            self._trash_line(other_line)
            self._trash_line(line)
        else:
            line.set_type(Line.TYPE_MISSING)
            other_line.set_type(Line.TYPE_INSERTED)
        self._to_render.append(lineno)

    def _set_line_type(self, diff_view, lineno, type):
        other_view = self._other(diff_view)
        line = diff_view.get_lines().get_line(lineno)
        other_line = other_view.get_lines().get_line(lineno)
        if type == Line.TYPE_INSERTED:
            other_line.set_type(Line.TYPE_MISSING)
        elif type == Line.TYPE_MISSING:
            if not other_line.is_missing():
                other_line.set_type(Line.TYPE_INSERTED)
        elif type == Line.TYPE_EQUAL:
            other_line.set_type(Line.TYPE_EQUAL)
        elif type == Line.TYPE_CHANGE:
            other_line.set_type(Line.TYPE_CHANGE)
        line.set_type(type)
        self._to_render.append(lineno)
