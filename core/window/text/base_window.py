import sublime, threading, gc
from ...object import Object
from ...diff.intralines import DiffIntralines
from ...task_manager import TaskManager
from ...utils import similarity_ratio, get_syntax_name, get_file_type_from_view
from ...settings import Settings
from ...debug import console
from ...themer import Themer
from ...promise import Promise
from ...promise_progress import PromiseProgress
from ..view.history import DiffViewHistory
from ..view.diff_view import DiffView
from ..base_window import BaseWindow
from .summary_panel import DiffWindowSummaryPanel
from .line_highlighter import LineHighlighter
from .behaviors.window_changes import BehaviorWindowChanges
from .behaviors.status_settings import BehaviorStatusSettings

class BaseDiffWindow(BaseWindow, BehaviorWindowChanges, BehaviorStatusSettings):
    EVENTS = [
     "destroy", "diff_done", "diff_start"]

    def __init__(self, close_promise, window_mode):
        BaseWindow.__init__(self, close_promise, window_mode)
        self._loading_promise = None
        self._is_diffing = False
        self._seq_number = -1
        self._thread = None
        self._history = DiffViewHistory(self)
        self._line_highlighter = LineHighlighter(self)
        self._summary_panel = DiffWindowSummaryPanel(self)
        self._selection_modified_promise = None
        self._cursor_pos_refresh = {}
        self._intralines = {}
        BehaviorWindowChanges.__init__(self)
        BehaviorStatusSettings.__init__(self)
        return

    def destroy(self, close_window=True):
        if self._destroyed:
            return
        self._loading_promise.reject()
        self._summary_panel.destroy()
        self._history.destroy()
        self._line_highlighter.destroy()
        BaseWindow.destroy(self, close_window)

    def close(self):
        diff_view = self._layout.get_focused_view()
        diff_view.get_view().close()

    def save(self):
        if not Settings.get("save_and_stay"):
            self.close()

    def can_close(self):
        return self._loading_promise.is_resolved() or self._loading_promise.is_rejected()

    def _highlight_corresponding_lines(self, force=False):
        self._line_highlighter.highlight(self._layout.get_focused_view(), force)
        self._summary_panel.refresh(self._layout.get_focused_view())

    def remove_intraline_changes(self):
        for key in list(self._intralines.keys()):
            self._intralines[key].destroy()

    def highlight_intraline_changes(self):
        if not Settings.get("intraline_analysis"):
            return
        diff_views = self._layout.get_active_views()
        diff_view_a = self._layout.get_left()
        diff_view_b = self._layout.get_right()
        groups_a = diff_view_a.get_lines().get_groups()
        groups_b = diff_view_b.get_lines().get_groups()
        if len(groups_a) == len(groups_b):
            for i, group_a in enumerate(groups_a):
                lines_b = groups_b[i].get_lines()
                for n, line_a in enumerate(group_a.get_lines()):
                    line_b = lines_b[n]
                    self._highlight_intraline_changes_on_lines(line_a, line_b)

    def _highlight_intraline_changes_on_lines(self, line_a, line_b):
        if not Settings.get("intraline_analysis") or line_a.get_type() == line_a.TYPE_MISSING or line_b.get_type() == line_b.TYPE_MISSING:
            return
        key = "%s-%s" % (id(line_a), id(line_b))
        if key in self._intralines and not self._intralines[key].is_destroyed():
            self._intralines[key].refresh()
            return
        intralines = DiffIntralines(line_a, line_b)
        self._intralines.update({key: intralines})
        line_a.on("destroy", (lambda sender: intralines.destroy()))
        line_b.on("destroy", (lambda sender: intralines.destroy()))

        def _on_intraline_destroy(intraline):
            try:
                del self._intralines[key]
            except:
                pass

        intralines.on("destroy", _on_intraline_destroy)

    def _open_file(self, diff_file, group):
        diff_view = DiffView(self, diff_file=diff_file, view=diff_file.get_view() if self._window_mode in [self.WINDOW_MODE_CURRENT] else None)
        self._add_diff_view(diff_view, group)
        return diff_view

    def _add_diff_view(self, diff_view, group):
        BaseWindow._add_diff_view(self, diff_view, group)
        diff_view.get_loaded_promise().then((lambda *result: self._on_view_load(diff_view)))
        self._track_view(diff_view)

    def _on_view_load(self, diff_view):
        Settings.load(get_syntax_name(diff_view.get_view()), True)

    def _on_selection_modified(self, diff_view, scroll_to=True):
        if not diff_view.is_loaded() or self._is_diffing:
            return
        if self._selection_modified_promise:
            self._selection_modified_promise.reject()

        def inner():
            self._line_highlighter.highlight(diff_view)
            self._line_similarity_status(diff_view)
            self._summary_panel.refresh(diff_view)
            self._history.initialize_selection()
            sel = diff_view.get_view().sel()
            self.selection_modified(diff_view, sel)
            if len(sel) == 1:
                if scroll_to:
                    diff_view.scroll_to(sel[0])

        self._selection_modified_promise = Promise().then(inner)
        sublime.set_timeout(self._selection_modified_promise.resolve, 5)

    def _on_swap(self):
        diff_view = self.get_focused_view()
        self._line_similarity_status(diff_view)
        self._summary_panel.refresh(diff_view)

    def _line_similarity_status(self, diff_view):
        if self._destroyed:
            return
        else:
            views = self._layout.get_active_views()
            sel = diff_view.get_view().sel()
            if len(sel) == 0:
                return
            row, _ = diff_view.get_view().rowcol(sel[0].begin())
            line_a = views[0].get_lines().get_line(row)
            line_b = views[-1].get_lines().get_line(row)
            if line_a.get_type() == line_a.TYPE_MISSING:
                pass
            self._set_status("similarity", "Left Line Missing")
            return
        if line_b.get_type() == line_b.TYPE_MISSING:
            self._set_status("similarity", "Right Line Missing")
            return
        ratio = similarity_ratio(line_a.get_view_text(), line_b.get_view_text())
        if ratio == 0:
            similarity = "Lines Different"
        elif ratio == 100:
            similarity = "Lines Identical"
        else:
            similarity = "Lines %d%% Similar" % ratio
        self._set_status("similarity", "%s" % similarity)

    def _setup_syntax(self, diff_views):
        views_to_setup = []
        syntax_to_set = None
        for diff_view in diff_views:
            view = diff_view.get_view()
            syntax_name, syntax_file = get_file_type_from_view(diff_view.get_diff_file().get_view() or diff_view.get_view())
            if view:
                if syntax_name not in (None, 'Plain text'):
                    syntax_to_set = syntax_file
                views_to_setup.append(view)
                continue

        if syntax_to_set:
            for view in views_to_setup:
                view.set_syntax_file(syntax_to_set)

        return

    def _initialize_diff_thread(self, views):
        return self.DiffThreadClass(*views)

    def _run_diff_when_all_loaded(self):
        views = self._layout.get_active_views()

        def check_all():
            if all(view.get_loaded_promise().is_resolved() for view in views):
                self._run_diff(deferred=False, threaded=True)

        for view in views:
            view.get_loaded_promise().then(check_all)

    def _run_diff(self, deferred=False, threaded=False):
        if self._is_diffing:
            return
        views = self._layout.get_active_views()
        if not self._is_diffing:
            self._loading_promise = Promise()
            PromiseProgress(self._loading_promise, "Loading diff")
            self._is_diffing = True
            self._setup_syntax(views)
            self.fire("diff_start")
            self._layout.stop_sync()
            for view in views:
                view.set_silent("selection_modified", True)

            def inner():
                self._thread = self._initialize_diff_thread(views)
                self._thread.on("change", self._handle_diff_change)
                self._thread.on("done", self._handle_diff_done)
                if threaded:
                    self._thread.run()
                else:
                    self._thread.run()
                while views:
                    views.pop()

            sublime.set_timeout(inner, 100 if deferred else 0)

    def refresh(self):
        if self._is_diffing:
            return
        for diff_view in self.get_active_views():
            self._cursor_pos_refresh.update({(diff_view.get_view().id()): (diff_view.get_view().sel()[0])})
            diff_view.reset()

        self._history.reset()
        self._run_diff(threaded=True)

    def _handle_diff_change(self, *args):
        self._seq_number = args[1]
        self._on_diff_change(*args)

    def _handle_diff_done(self, *args):
        focus_tasks = TaskManager(10)

        def focus_task(v):
            return (lambda : v.focus())

        self._layout.sync_to_active()
        self._layout.start_sync()

        def on_done(*args):
            for diff_view in self.get_active_views():
                view = diff_view.get_view()
                view.sel().clear()
                view.sel().add(self._cursor_pos_refresh[view.id()] if view.id() in self._cursor_pos_refresh else sublime.Region(0, 0))
                diff_view.set_silent("selection_modified", False)
                focus_tasks.add(focus_task(diff_view))

            self._highlight_corresponding_lines()
            self._line_similarity_status(diff_view)
            self._history.initialize()
            left = self._layout.get_left()
            right = self._layout.get_right()
            self._layout.unfreeze()
            Themer.force_reload()
            if self.is_2way():
                if not right.is_read_only():
                    focus_tasks.add(focus_task(right))
                elif not left.is_read_only():
                    focus_tasks.add(focus_task(left))
                else:
                    focus_tasks.add(focus_task(right))
            else:
                focus_tasks.add(focus_task(self._layout.get_merged()))
            self.highlight_intraline_changes()

            def done():
                self._is_diffing = False
                self._loading_promise.resolve()
                for diff_view in self.get_active_views():
                    diff_view.apply_read_only()
                    diff_view.fire("selection_modified")

                self._changes_behavior_on_diff_done()
                self.fire("diff_done")

            sublime.set_timeout(done, 50)

        self._on_diff_done(*args).then(on_done)

    def _on_diff_done(self, *args):
        pass

    def _add_change(self, diff_change):
        self._changes.update({(diff_change.get_number()): diff_change})

    def on_show_panel(self, panel):
        self._summary_panel.on_show_panel(panel)
        self._line_highlighter.on_show_panel()

    def on_hide_panel(self):
        self._line_highlighter.on_hide_panel()
        return self._summary_panel.on_hide_panel()
