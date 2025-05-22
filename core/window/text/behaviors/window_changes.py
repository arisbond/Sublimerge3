import sublime
from ....observable import Observable
from ....renderers.groups_renderers import GutterRenderer, Renderer
from ....settings import Settings
from ....object import Object
from ....lines.line import Line
from ....menu import Menu, MenuItem
from ....task import Task
from ....utils import sort

class DiffChange(Observable):
    EVENTS = [
     "destroy"]
    NUM = 0
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_window, groups, diff_views):
        if Object.DEBUG:
            Object.add(self)
        Observable.__init__(self)
        self._selected = False
        self._deselect_on_selection_change = True
        if diff_window.is_3way():
            self._pairs = [[groups[0], diff_views[0]],
             [
              groups[1], diff_views[1]],
             [
              groups[2], diff_views[2]]]
        else:
            self._pairs = [[groups[0], diff_views[0]],
             [
              groups[1], diff_views[1]]]
        self._diff_window = diff_window
        self._name = "change-%d" % DiffChange.NUM
        DiffChange.NUM += 1
        for group in groups:
            group.on("destroy", self._on_group_destroy)

        diff_window.get_layout().on("swap", self._on_window_swap)

    def destroy(self):
        try:
            self._diff_window.get_layout().un("swap", self._on_window_swap)
        except:
            pass

        self.fire("destroy")
        self.un()
        while self._pairs:
            group, view = self._pairs.pop()
            group.un("destroy", self._on_group_destroy)

        self._pairs = []

    def is_conflict(self):
        return self._pairs[0][0].get_lines()[0].is_conflict()

    def is_resolved(self):
        return self._diff_window.is_3way() and any([not v.is_missing() for v in self._pairs[1][0].get_lines()])

    def get_lineno_begin(self):
        return self._pairs[0][0].get_lines()[0].get_lineno()

    def get_lineno_end(self):
        return self._pairs[0][0].get_lines()[-1].get_lineno()

    def scroll_to(self):
        for item in self._pairs:
            item[1].scroll_to(item[0].get_region())

    def select(self, select_line=True):
        self._selected = True
        active_view = self._diff_window.get_focused_view()
        for group, diff_view in self._pairs:
            if select_line:
                diff_view.set_silent("selection_modified", True)
                row, col = diff_view.get_view().rowcol(group.get_region().begin())
                diff_view.move_caret_to(row, 0)
                diff_view.set_silent("selection_modified", False)
            Renderer.render_selected(diff_view.get_view(), group)

        active_view.fire("selection_modified", False)

    def deselect(self):
        self._selected = False
        for group, diff_view in self._pairs:
            Renderer.render_unselected(diff_view.get_view(), group)

    def is_selected(self):
        return self._selected

    def get_navigator_info(self):
        return (
         self._pairs[0][0].get_lines(), self._pairs[-1][0].get_lines())

    def copy(self, source, target):
        source_group, source_view = self._pairs[source]
        target_group, target_view = self._pairs[target]
        target_region = target_group.get_region()
        source_region = source_group.get_region()
        target_view.get_view().set_scratch(False)
        last_line = target_group.get_lines()[-1]
        if self._diff_window.is_2way():
            target_view.set_silent("modified", True)
            target_view.get_view().run_command("sublimerge_view_replace", {"begin": (target_region.begin()), 
             "end": (target_region.end()), 
             "text": (source_group.get_view_text())})
            target_view.set_silent("modified", False)
            source_view.set_silent("modified", True)
            source_view.get_view().run_command("sublimerge_view_replace", {"begin": (source_region.begin()), 
             "end": (source_region.end()), 
             "text": (source_group.get_view_text())})
            source_view.set_silent("modified", False)
            update_by = 0
            for line in reversed(source_group.get_lines()):
                if line.get_type() == line.TYPE_MISSING:
                    update_by += 1
                source_view.get_lines().set_line_type(line.get_lineno(), line.TYPE_EQUAL)

            for line in reversed(target_group.get_lines()):
                target_view.get_lines().set_line_type(line.get_lineno(), line.TYPE_EQUAL)

            source_view.get_lines().update_lineno_since(line.get_lineno(), -update_by)
            target_view.get_lines().update_lineno_since(line.get_lineno(), -update_by)
        else:
            lines_source = source_view.get_lines()
            lines_target = target_view.get_lines()
            lines = source_group.get_lines()
            for i, source_line in enumerate(lines):
                target_line = target_group.get_lines()[i]
                target_line.set_view_text(source_line.get_view_text())
                target_line.set_type(source_line.get_type())

            lines_target.render_changes(range(lines[0].get_lineno() - 1, lines[-1].get_lineno() + 2))
            lines_source.render_changes(range(lines[0].get_lineno() - 1, lines[-1].get_lineno() + 2))
        target_view.move_caret_to(last_line.get_lineno(), -1)
        target_view.focus()

    def copy_both(self, first, second):
        first_group, first_view = self._pairs[first]
        second_group, second_view = self._pairs[second]
        first_lines = first_view.get_lines()
        second_lines = second_view.get_lines()
        target_group, target_view = self._pairs[1]
        target_view.get_view().set_scratch(False)
        target_lines = target_view.get_lines()
        first_source_lines = first_group.get_lines()
        second_source_lines = second_group.get_lines()
        target_group_lines = target_group.get_lines()
        last_target_line = target_group_lines[-1]
        lineno_begin = last_target_line.get_lineno() + 1
        for i in range(len(target_group_lines)):
            target_group_lines[i].set_view_text(first_source_lines[i].get_view_text())
            target_group_lines[i].set_type(first_source_lines[i].get_type())

        for i in range(len(target_group_lines)):
            new_line = target_lines.create_empty_line(lineno_begin + i)
            new_line.set_change_type(last_target_line.get_change_type())
            new_line.set_type(second_source_lines[i].get_type())
            new_line.set_view_text(second_source_lines[i].get_view_text())
            new_line = first_lines.create_empty_line(lineno_begin + i)
            new_line.set_change_type(last_target_line.get_change_type())
            new_line.set_type(new_line.TYPE_MISSING)
            new_line = second_lines.create_empty_line(lineno_begin + i)
            new_line.set_change_type(last_target_line.get_change_type())
            new_line.set_type(new_line.TYPE_MISSING)

        lineno_begin = target_group_lines[0].get_lineno()
        first_lines.render_changes(range(lineno_begin - 1, new_line.get_lineno() + 2))
        second_lines.render_changes(range(lineno_begin - 1, new_line.get_lineno() + 2))
        target_lines.render_changes(range(lineno_begin - 1, new_line.get_lineno() + 2))
        target_view.move_caret_to(new_line.get_lineno(), -1)

    def _on_group_destroy(self, group):
        try:
            self._diff_window.get_layout().un("swap", self._on_window_swap)
        except:
            pass

        self.destroy()

    def _on_window_swap(self, sender):
        self._pairs = list(reversed(self._pairs))


class BehaviorWindowChanges:

    def __init__(self):
        self._caret_lineno = -1
        self._selected_change = None
        self._changes = []
        self._deselect_on_selection_change = True
        self._is_first_run = True
        self._changes_navigator_is_open = False
        self.on("destroy", self._changes_behavior_on_destroy)
        return

    def _changes_behavior_on_destroy(self, sender):
        while self._changes:
            self._changes.pop().destroy()

    def _changes_behavior_on_diff_done(self):
        self._refresh_changes()
        for diff_view in self.get_active_views():
            diff_view.get_lines().on("rendered", self._changes_behavior_on_lines_rendered)
            diff_view.on("selection_modified", self._changes_behavior_on_selection_modified)

        if len(self._changes) == 0:
            sublime.set_timeout((lambda : sublime.message_dialog("Sublimerge\n\nThere are no differences between inputs")), 500)
        elif self._is_first_run:
            if Settings.get("auto_select_first") and not self.get_selected_change():
                self.select_first_change()
        self._is_first_run = False

    def _changes_behavior_on_lines_rendered(self, sender):
        change = self.get_or_find_selected_change()
        if change:
            change.deselect()
        self._refresh_changes()

    def _changes_behavior_on_selection_modified(self, sender, *args):
        view = sender.get_view()
        sel = view.sel()
        if len(sel) == 1:
            point = sel[0].end()
            self._caret_lineno, _ = view.rowcol(point)
        if self._deselect_on_selection_change:
            self._deselect_selected_change()

    def _changes_behavior_on_change_destroy(self, change):
        if change.is_selected():
            change.deselect()
            self._selected_change = None
        try:
            self._changes.remove(change)
        except:
            pass

        return

    def _refresh_changes(self):
        for change in self._changes:
            change.destroy()

        diff_views = self.get_active_views()
        left = self._layout.get_left()
        right = self._layout.get_right()
        changes_a = left.get_changes()
        changes_b = right.get_changes()
        if self.is_3way():
            merged = self._layout.get_merged()
            changes_merged = merged.get_changes()
            len_merged = len(changes_merged)
        else:
            len_merged = len(changes_a)
        if len(changes_a) == len(changes_b) == len_merged:
            for i, change in enumerate(changes_a):
                if self.is_3way():
                    change = DiffChange(self, [
                     change, changes_merged[i], changes_b[i]], [
                     left, merged, right])
                else:
                    change = DiffChange(self, [
                     change, changes_b[i]], [
                     left, right])
                change.on("destroy", self._changes_behavior_on_change_destroy)
                self._changes.append(change)

        return self._changes

    def show_changes_navigator(self):
        if not self._changes or self._changes_navigator_is_open:
            return
        self._changes_navigator_is_open = True

        def on_changes_navigator_close(initial_change):
            if initial_change:
                self.set_selected_change(initial_change)
                initial_change.scroll_to()
            self._changes_navigator_is_open = False

        def inner():
            left_miss_count = 0
            right_miss_count = 0
            cut_size = 2
            initial_change = self.get_selected_change()
            menu = Menu(on_cancel=(lambda *args: on_changes_navigator_close(initial_change)), on_select=(lambda *args: on_changes_navigator_close(None)))
            for change in self._changes:
                left, right = change.get_navigator_info()
                left_not_miss = [v for v in left if not v.is_missing()]
                left_miss = [v for v in left if v.is_missing()]
                right_not_miss = [v for v in right if not v.is_missing()]
                right_miss = [v for v in right if v.is_missing()]
                left_begin = left_not_miss[0].get_lineno() - left_miss_count + 1 if left_not_miss else left_miss[0].get_lineno() - left_miss_count + 1
                left_size = len(left_not_miss)
                right_begin = right_not_miss[0].get_lineno() - right_miss_count + 1 if right_not_miss else right_miss[0].get_lineno() - right_miss_count + 1
                right_size = len(right_not_miss)
                title = "-%d,%d +%d,%d" % (left_begin, left_size, right_begin, right_size)
                left_lines = [
                 "?"] * cut_size
                right_lines = ["?"] * cut_size
                for i, line in enumerate(left_not_miss[:cut_size]):
                    left_lines[i] = "- " + line.get_view_text()[0:100]

                for i, line in enumerate(right_not_miss[:cut_size]):
                    right_lines[i] = "+ " + line.get_view_text()[0:100]

                if left_lines[-1] == "?":
                    if right_lines[-1] == "?":
                        left_lines[-1] = right_lines[0]
                        right_lines = [""] * cut_size
                menu.add_item(MenuItem(caption=[
                 title] + left_lines + right_lines, selected=change.is_selected(), value=change, on_over=(lambda item: self.set_selected_change(item.get_value(), False)), on_out=(lambda item: item.get_value().deselect()), on_select=(lambda item: self.set_selected_change(item.get_value()))))
                left_miss_count += len(left_miss)
                right_miss_count += len(right_miss)

            menu.show()

        Task.spawn(inner).progress("Inspecting changes...")

    def get_conflicts(self, resolved_only):
        return [v for v in self._changes if v.is_conflict() and not resolved_only or v.is_resolved()]

    def get_or_find_selected_change(self):
        if not self._selected_change:
            return self._find_change_under_caret()
        return self._selected_change

    def get_selected_change(self):
        return self._selected_change

    def get_previous_change(self, change_only=False):
        return self._find_changes_surrounding_caret()[0] or self._find_change_under_caret()

    def get_next_change(self, change_only=False):
        return self._find_changes_surrounding_caret()[1] or self._find_change_under_caret()

    def select_previous_change(self, change_only=False):
        self._select_change(0)

    def select_next_change(self, change_only=False):
        self._select_change(1)

    def select_change_under_caret(self):
        change = self._find_change_under_caret()
        if change:
            self.set_selected_change(change)

    def select_first_change(self):
        changes = self.get_navigatable_changes()
        self.set_selected_change(changes[0] if len(changes) > 0 else None)
        return

    def _select_change(self, index):
        change = self._find_change_under_caret()
        if not change or change.is_selected():
            change = self._find_changes_surrounding_caret()[index]
        self.set_selected_change(change)

    def set_selected_change(self, change, goto_line=True):
        if change:
            self._deselect_on_selection_change = False
            self._deselect_selected_change()
            change.select(goto_line)
            change.scroll_to()
            self._selected_change = change
            self._deselect_on_selection_change = True

    def copy_selected_change(self, source, target):
        change = self.get_selected_change()
        if change:
            change.copy(source, target)
            self._history.snapshot()
            if self.is_3way():
                self.select_change_under_caret()
            if Settings.get("go_to_next_after_merge"):
                self.select_next_change()

    def copy_selected_change_both(self, first, second):
        change = self.get_selected_change()
        if change:
            change.copy_both(first, second)
            self._history.snapshot()
            if self.is_3way():
                self.select_change_under_caret()
            if Settings.get("go_to_next_after_merge"):
                self.select_next_change()

    def can_copy_single_line(self, source, target):
        line = self.get_active_views()[target].get_lines().get_line(self._caret_lineno)
        return line.get_type() != line.TYPE_EQUAL

    def copy_single_line(self, source, target):
        source_view = self.get_active_views()[source]
        target_view = self.get_active_views()[target]
        lines_source = source_view.get_lines()
        lines_target = target_view.get_lines()
        line_source = lines_source.get_line(self._caret_lineno)
        line_target = lines_target.get_line(self._caret_lineno)
        target_view.get_view().set_scratch(False)
        if self.is_2way() and line_source.get_type() == line_source.TYPE_MISSING:
            lines_source.remove_line(self._caret_lineno)
            lines_target.remove_line(self._caret_lineno)
        else:
            line_target.set_view_text(line_source.get_view_text())
            if self.is_2way():
                line_target.set_type(line_target.TYPE_EQUAL)
                line_source.set_type(line_source.TYPE_EQUAL)
            else:
                line_target.set_type(line_source.get_type())
            lines_target.render_changes(range(self._caret_lineno - 1, self._caret_lineno + 2))
            lines_source.render_changes(range(self._caret_lineno - 1, self._caret_lineno + 2))
        target_view.move_caret_to(self._caret_lineno, -1)
        target_view.focus()
        self._history.snapshot()

    def copy_single_line_after(self, source, target):
        print("copy_single_line_after - to be implemented")

    def copy_all_changes(self, source, target):
        source_view = self.get_active_views()[source]
        target_view = self.get_active_views()[target]
        if self.is_2way():
            lines_source = source_view.get_lines()
            lines_target = target_view.get_lines()
            text_source = source_view.get_text()
            for lineno in lines_source:
                line_source = lines_source.get_line(lineno)
                line_target = lines_target.get_line(lineno)
                lines_source.destroy_and_remove(line_source)
                lines_target.destroy_and_remove(line_target)

            source_view.set_silent("modified", True)
            source_view.get_view().run_command("sublimerge_view_replace", {"begin": 0, 
             "end": (source_view.get_view().size()), 
             "text": text_source})
            source_view.set_silent("modified", False)
            target_view.get_view().set_scratch(False)
            target_view.set_silent("modified", True)
            target_view.get_view().run_command("sublimerge_view_replace", {"begin": 0, 
             "end": (target_view.get_view().size()), 
             "text": text_source})
            target_view.set_silent("modified", False)
        else:
            for change in self._changes:
                change.copy(source, target)

        target_view.move_caret_to(self._caret_lineno - 1, -1)
        target_view.focus()
        self._history.snapshot()

    def get_navigatable_changes(self):
        conflicts_only = self.is_3way() and not Settings.get("three_way_navigate_all")
        return [v for v in self._changes if not conflicts_only or v.is_conflict()]

    def _find_changes_surrounding_caret(self):
        changes = self.get_navigatable_changes()

        def result():
            x = self._caret_lineno
            lo = 0
            hi = len(changes)
            right = None
            while lo < hi:
                mid = (lo + hi) // 2
                midval = changes[mid]
                end = midval.get_lineno_end()
                begin = midval.get_lineno_begin()
                if end < x:
                    lo = mid + 1
                elif begin > x:
                    hi = mid
                    if right is None or mid < right:
                        right = mid
                else:
                    return [
                     mid - 1, mid + 1]

            if right is None:
                right = len(changes)
            return [right - 1, right]

        res = result()
        if res[0] < 0:
            res[0] = None
        else:
            res[0] = changes[res[0]]
        if res[1] > len(changes) - 1:
            res[1] = None
        else:
            res[1] = changes[res[1]]
        return res

    def _find_change_under_caret(self):
        a = self.get_navigatable_changes()
        x = self._caret_lineno
        lo = 0
        hi = len(a)
        while lo < hi:
            mid = (lo + hi) // 2
            midval = a[mid]
            end = midval.get_lineno_end()
            begin = midval.get_lineno_begin()
            if end < x:
                lo = mid + 1
            elif begin > x:
                hi = mid
            else:
                return midval

        return

    def _deselect_selected_change(self):
        change = self.get_selected_change()
        if change:
            if change.is_selected():
                change.deselect()
                self._selected_change = None
        return
