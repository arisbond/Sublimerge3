import sublime
from time import sleep
from ....utils import prepare_to_compare, splitlines
from ....lines.line import Line
from .diff_live_base import DiffLiveBase

class BehaviorWindowDiffLive3(DiffLiveBase):

    def modified(self, diff_view, modified, removed, inserted):
        if not removed and not inserted and modified:
            self._on_line_modified(diff_view, modified[0])
        elif removed:
            if modified:
                lines = diff_view.get_lines()
                left_view, right_view = self._other(diff_view)
                left_lines = left_view.get_lines()
                right_lines = right_view.get_lines()
                for lineno in removed:
                    lines.get_line(lineno)
                    left_line = left_lines.get_line(lineno)
                    right_line = right_lines.get_line(lineno)
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
        merged_line = diff_view.get_lines().get_line(row)
        next_merged_line = diff_view.get_lines().get_line(row + 1)

        def is_caret_at_line_begin():
            return col == 0

        def is_caret_at_line_end():
            return col == merged_line.get_region().size() - 1

        def is_caret_at_line_middle():
            return col > 0 and col < merged_line.get_region().size() - 1

        def is_line_with_caret_empty():
            return merged_line.get_region().size() == 1

        left_view, right_view = self._other(diff_view)
        left_lines = left_view.get_lines()
        right_lines = right_view.get_lines()
        if merged_line.is_missing():
            self._on_line_modified(diff_view, row)
            self._apply()
            return False
        if next_merged_line.is_missing() and (is_caret_at_line_end() or is_line_with_caret_empty()):
            self._on_line_modified(diff_view, row + 1)
            self._move_caret_to_line_end(diff_view, row + 1)
            self._apply()
            return False
        if is_caret_at_line_begin():
            left_lines.create_empty_line(row)
            right_lines.create_empty_line(row)
            diff_view.get_lines().create_empty_line(row)
            self._move_caret_to_line_begin(diff_view, row + 1)
            self._set_line_type(diff_view, row, Line.TYPE_INSERTED)
            self._apply()
            return False
        if is_caret_at_line_end():
            left_lines.create_empty_line(row + 1)
            right_lines.create_empty_line(row + 1)
            diff_view.get_lines().create_empty_line(row + 1)
            self._move_caret_to_line_begin(diff_view, row + 1)
            self._set_line_type(diff_view, row + 1, Line.TYPE_INSERTED)
            self._apply()
            return False
        if is_caret_at_line_middle():
            text_left = merged_line.get_view_text()[:col]
            text_right = merged_line.get_view_text()[col:]
            merged_line.set_view_text(text_left)
            self._on_line_modified(diff_view, row)
            left_lines.create_empty_line(row + 1)
            right_lines.create_empty_line(row + 1)
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
        self._join_lines_before_missings_left(diff_view, current_line)
        self._apply()
        return False

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
        self._join_lines_before_missings_right(diff_view, current_line)
        self._apply()
        return False

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
        left_view, right_view = self._other(diff_view)
        left_lines = left_view.get_lines()
        right_lines = right_view.get_lines()
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
                left_lines.create_empty_line(row + i)
                right_lines.create_empty_line(row + i)
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
        left_view, right_view = self._other(diff_view)
        modified_line = diff_view.get_lines().get_line(lineno)
        left_line = left_view.get_lines().get_line(lineno)
        right_line = right_view.get_lines().get_line(lineno)
        if self._lines_equals(modified_line, left_line) and self._lines_equals(modified_line, right_line):
            self._set_line_type(diff_view, lineno, Line.TYPE_EQUAL)
        else:
            self._set_line_type(diff_view, lineno, Line.TYPE_CHANGE)

    def _remove_line(self, diff_view, lineno):
        left_view, right_view = self._other(diff_view)
        merged_line = diff_view.get_lines().get_line(lineno)
        left_line = left_view.get_lines().get_line(lineno)
        right_line = right_view.get_lines().get_line(lineno)
        if left_line.is_missing() and right_line.is_missing():
            self._trash_line(left_line)
            self._trash_line(right_line)
            self._trash_line(merged_line)
        else:
            merged_line.set_type(Line.TYPE_MISSING)
        if not left_line.is_missing():
            left_line.set_type(Line.TYPE_INSERTED)
        if not right_line.is_missing():
            right_line.set_type(Line.TYPE_INSERTED)
        self._to_render.append(lineno)

    def _set_line_type(self, merged_view, lineno, type):
        left_view, right_view = self._other(merged_view)
        merged_line = merged_view.get_lines().get_line(lineno)
        left_line = left_view.get_lines().get_line(lineno)
        right_line = right_view.get_lines().get_line(lineno)
        if type == Line.TYPE_EQUAL:
            if not left_line.is_missing() and not right_line.is_missing():
                left_line.set_type(Line.TYPE_EQUAL)
                right_line.set_type(Line.TYPE_EQUAL)
                merged_line.set_type(Line.TYPE_EQUAL)
            else:
                merged_line.set_type(Line.TYPE_CHANGE)
        elif type == Line.TYPE_CHANGE:
            if not left_line.is_missing():
                if not right_line.is_missing():
                    left_line.set_type(Line.TYPE_CHANGE)
                    right_line.set_type(Line.TYPE_CHANGE)
            merged_line.set_type(Line.TYPE_CHANGE)
        elif type == Line.TYPE_INSERTED:
            left_line.set_type(Line.TYPE_MISSING)
            right_line.set_type(Line.TYPE_MISSING)
            merged_line.set_type(Line.TYPE_INSERTED)
        elif type == Line.TYPE_MISSING:
            if not left_line.is_missing():
                left_line.set_type(Line.TYPE_MISSING)
            if not right_line.is_missing():
                right_line.set_type(Line.TYPE_MISSING)
        self._to_render.append(lineno)
