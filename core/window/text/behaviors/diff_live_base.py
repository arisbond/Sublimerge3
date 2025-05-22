import sublime
from time import sleep
from .tracker import Tracker
from ....utils import prepare_to_compare, splitlines
from ....lines.line import Line

class DiffLiveBase:

    def __init__(self):
        self._trackers = []
        self._to_render = []
        self._to_remove = []

    def destroy(self):
        for tracker in self._trackers:
            tracker.un()
            tracker.destroy()

        self._trackers = None
        return

    def _track_view(self, diff_view):
        tracker = Tracker(diff_view)
        tracker.on("modified", (lambda tracker, modified, removed, inserted: self.modified(diff_view, modified, removed, inserted)))
        diff_view.get_lines().on("render_line", self._on_render_line)
        self._trackers.append(tracker)

    def undo(self, diff_view):
        self._history.undo(diff_view)

    def redo(self, diff_view):
        self._history.redo(diff_view)

    def selection_modified(self, diff_view, selection):
        pass

    def cut(self, diff_view):
        view = diff_view.get_view()
        sel = diff_view.get_view().sel()
        if len(sel) == 1:
            text = diff_view.get_lines().get_text(sel[0])
            sublime.set_clipboard(text)
            self.left_delete(diff_view)
        return False

    def copy(self, diff_view):
        view = diff_view.get_view()
        sel = diff_view.get_view().sel()
        if len(sel) == 1:
            text = diff_view.get_lines().get_text(sel[0])
            sublime.set_clipboard(text)
        return False

    def swap_line_down(self, diff_view):
        sel_begin = self._selection_begin(diff_view)
        sel_end = self._selection_end(diff_view)
        if not sel_begin or sel_begin != sel_end:
            return False
        row, col = sel_begin
        lines = diff_view.get_lines()
        line1 = lines.get_line(row)
        if line1.is_missing():
            return False
        line2 = lines.get_line(row + 1)
        while line2 and line2.is_missing():
            line2 = lines.get_line(line2.get_lineno() + 1)

        if not line1 or not line2:
            return False
        line_text_1 = line1.get_view_text()
        line_text_2 = line2.get_view_text()
        line2.set_view_text(line_text_1)
        line1 = diff_view.get_lines().get_line(row)
        line1.set_view_text(line_text_2)
        self._on_line_modified(diff_view, line1.get_lineno())
        self._on_line_modified(diff_view, line2.get_lineno())
        self._apply()
        return False

    def swap_line_up(self, diff_view):
        sel_begin = self._selection_begin(diff_view)
        sel_end = self._selection_end(diff_view)
        if not sel_begin or sel_begin != sel_end:
            return False
        row, col = sel_begin
        lines = diff_view.get_lines()
        line1 = lines.get_line(row)
        if line1.is_missing():
            return False
        line2 = lines.get_line(row - 1)
        while line2 and line2.is_missing():
            line2 = lines.get_line(line2.get_lineno() - 1)

        if not line1 or not line2:
            return False
        line_text_1 = line1.get_view_text()
        line_text_2 = line2.get_view_text()
        line2.set_view_text(line_text_1)
        line1 = diff_view.get_lines().get_line(row)
        line1.set_view_text(line_text_2)
        self._on_line_modified(diff_view, line2.get_lineno())
        self._on_line_modified(diff_view, line1.get_lineno())
        self._apply()
        return False

    def duplicate_line(self, diff_view):
        pass

    def _delete_selection(self, diff_view, begin, end):
        row_begin, col_begin = begin
        row_end, col_end = end
        selection = diff_view.get_view().sel()
        if row_begin == row_end:
            diff_view.get_view().run_command("sublimerge_view_replace", {"begin": (selection[0].begin()), 
             "end": (selection[0].end()), 
             "text": ""})
            return False
        else:
            lines_with_selection = [v for v in range(row_begin, row_end + 1)]
            lines_to_remove = lines_with_selection[:]
            if col_begin > 0 or col_end > 0:
                lines_to_remove = lines_to_remove[1:]
            text_to_put = diff_view.get_lines().get_line(row_end).get_view_text()[col_end:] if col_end >= 0 else None
            for lineno in lines_to_remove:
                self._remove_line(diff_view, lineno)

            if text_to_put is not None:
                diff_view.get_view().run_command("sublimerge_view_replace", {"begin": (selection[0].begin()), 
                 "end": (diff_view.get_lines().get_line(row_begin).get_region().end() - 1), 
                 "text": text_to_put})
                self._on_line_modified(diff_view, row_begin)
            self._apply()
            self._move_caret_to_line_col(diff_view, row_begin, col_begin)
            return False

    def _selection_begin(self, diff_view):
        sel = diff_view.get_view().sel()
        if len(sel) != 1:
            return False
        return diff_view.get_view().rowcol(sel[0].begin())

    def _selection_end(self, diff_view):
        sel = diff_view.get_view().sel()
        if len(sel) != 1:
            return False
        return diff_view.get_view().rowcol(sel[0].end())

    def _other(self, diff_view):
        views = [v for v in self._views if v is not diff_view]
        if len(views) == 1:
            return views[0]
        return views

    def _lines_equals(self, a, b):
        return prepare_to_compare(a.get_view_text()) == prepare_to_compare(b.get_view_text())

    def _on_render_line(self, diff_lines, line):
        if self._is_diffing:
            return
        views = self._layout.get_active_views()
        self._highlight_intraline_changes_on_lines(views[0].get_lines().get_line(line.get_lineno()), views[-1].get_lines().get_line(line.get_lineno()))

    def _move_caret_before_missings(self, diff_view, line):
        view = diff_view.get_view()
        lines = diff_view.get_lines()
        while line and line.is_missing():
            line = lines.get_line(line.get_lineno() - 1)

        if not line:
            line = lines.get_line(0)
        view.sel().clear()
        point = max(line.get_region().end() - 1, 0)
        view.sel().add(sublime.Region(point, point))
        diff_view.fire("selection_modified")

    def _move_caret_after_missings(self, diff_view, line):
        view = diff_view.get_view()
        lines = diff_view.get_lines()
        while line and line.is_missing():
            line = lines.get_line(line.get_lineno() + 1)

        if not line:
            line = lines.get_line(len(lines.get_lines()) - 1)
        view.sel().clear()
        point = line.get_region().begin()
        view.sel().add(sublime.Region(point, point))
        diff_view.fire("selection_modified")

    def _move_caret_to_line_end(self, diff_view, lineno):
        line = diff_view.get_lines().get_line(lineno)
        view = diff_view.get_view()
        view.sel().clear()
        point = line.get_region().end() - 1
        view.sel().add(sublime.Region(point, point))
        diff_view.fire("selection_modified")

    def _move_caret_to_line_begin(self, diff_view, lineno):
        line = diff_view.get_lines().get_line(lineno)
        view = diff_view.get_view()
        view.sel().clear()
        point = line.get_region().begin()
        view.sel().add(sublime.Region(point, point))
        diff_view.fire("selection_modified")

    def _move_caret_to_line_col(self, diff_view, lineno, col):
        line = diff_view.get_lines().get_line(lineno)
        view = diff_view.get_view()
        view.sel().clear()
        point = line.get_region().begin() + col
        view.sel().add(sublime.Region(point, point))
        diff_view.fire("selection_modified")

    def _join_lines_before_missings_left(self, diff_view, current_line):
        view = diff_view.get_view()
        lines = diff_view.get_lines()
        first_non_missing_line = lines.get_line(current_line.get_lineno() - 1)
        while first_non_missing_line and first_non_missing_line.is_missing():
            first_non_missing_line = lines.get_line(first_non_missing_line.get_lineno() - 1)

        if first_non_missing_line:
            if not first_non_missing_line.is_missing():
                lineno = current_line.get_lineno()
                text = current_line.get_view_text()
                self._remove_line(diff_view, lineno)
                point = first_non_missing_line.get_region().end() - 1
                view.run_command("sublimerge_view_insert", {"begin": point, 
                 "text": text})
                self._to_render.append(first_non_missing_line.get_lineno())
                self._on_line_modified(diff_view, first_non_missing_line.get_lineno())
                view.sel().clear()
                view.sel().add(sublime.Region(point, point))
                self._apply()
        return False

    def _join_lines_before_missings_right(self, diff_view, current_line):
        view = diff_view.get_view()
        lines = diff_view.get_lines()
        first_non_missing_line = lines.get_line(current_line.get_lineno() + 1)
        while first_non_missing_line and first_non_missing_line.get_type() == first_non_missing_line.TYPE_MISSING:
            first_non_missing_line = lines.get_line(first_non_missing_line.get_lineno() + 1)

        if first_non_missing_line:
            if not first_non_missing_line.is_missing():
                if first_non_missing_line.get_pointer().end() >= diff_view.get_view().size() - 1:
                    return False
                lineno = first_non_missing_line.get_lineno()
                text = first_non_missing_line.get_view_text()
                self._remove_line(diff_view, lineno)
                point = current_line.get_region().end() - 1
                view.run_command("sublimerge_view_insert", {"begin": point, 
                 "text": text})
                self._to_render.append(current_line.get_lineno())
                point += len(text)
                view.sel().clear()
                view.sel().add(sublime.Region(point, point))
                self._apply()
        return False

    def _trash_line(self, line):
        self._to_remove.append((line, line.get_owning_lines()))

    def _apply(self):
        for line, lines in self._to_remove:
            lines.remove_line(line.get_lineno())
            self._to_render.append(line.get_lineno())

        self._to_remove = []
        if self._to_render:
            to_render = range(min(self._to_render) - 2, max(self._to_render) + 2)
            for diff_view in self._layout.get_active_views():
                diff_view.get_lines().render_changes(to_render)

        self._to_render = []
        self.get_focused_view().fire("selection_modified")
        self._history.snapshot()
        self.get_focused_view().get_view().set_scratch(False)
