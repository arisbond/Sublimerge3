import sublime, os
from ...diff.thread import DiffThread2, DiffThread3
from ...task import Task
from ...promise import Promise
from ...vcs.vcs import VCS
from ...debug import console
from ...settings import Settings
from ..layout import DiffWindowLayout2, DiffWindowLayout3, DiffWindowLayoutTextAndDirectories
from ..view.diff_view import DiffView
from .behaviors.diff_live2 import BehaviorWindowDiffLive2
from .behaviors.diff_live3 import BehaviorWindowDiffLive3
from .base_window import BaseDiffWindow

class DiffWindow2(BaseDiffWindow, BehaviorWindowDiffLive2):
    DiffThreadClass = DiffThread2
    DiffWindowLayoutClass = DiffWindowLayout2

    def __init__(self, close_promise, left_file, right_file, window_mode=BaseDiffWindow.WINDOW_MODE_NEW):
        BaseDiffWindow.__init__(self, close_promise, window_mode)
        BehaviorWindowDiffLive2.__init__(self)
        self._open_file(left_file, 0)
        self._open_file(right_file, 1)
        self._run_diff_when_all_loaded()

    def is_2way(self):
        return True

    def is_3way(self):
        return False

    def save(self):
        diff_view = self._layout.get_focused_view()
        if not diff_view.is_read_only():
            diff_view.get_view().run_command("save")
        BaseDiffWindow.save(self)

    def _on_diff_change(self, sender, seq_number, change_left, change_right):
        left = self._layout.get_left()
        right = self._layout.get_right()
        left.get_lines().render_hunk(change_left)
        right.get_lines().render_hunk(change_right)

    def _on_diff_done(self, sender, view_a, view_b):
        view_a.get_lines().prepare_to_flush()
        view_b.get_lines().prepare_to_flush()
        return Promise.all([
         Task.spawn((lambda : view_a.get_lines().flush())),
         Task.spawn((lambda : view_b.get_lines().flush()))])


class DiffWindowTextInDirectories(DiffWindow2):
    DiffWindowLayoutClass = DiffWindowLayoutTextAndDirectories

    def _open_file(self, diff_file, group):
        DiffWindow2._open_file(self, diff_file, group + 2)

    def destroy(self, close_window=False):
        for view in self._views:
            try:
                view.get_view().close()
            except:
                pass

        DiffWindow2.destroy(self, False)


class DiffWindow3(BaseDiffWindow, BehaviorWindowDiffLive3):
    DiffThreadClass = DiffThread3
    DiffWindowLayoutClass = DiffWindowLayout3

    def __init__(self, close_promise, their_file, base_file, mine_file, merged_file, window_mode=BaseDiffWindow.WINDOW_MODE_NEW):
        BaseDiffWindow.__init__(self, close_promise, window_mode)
        BehaviorWindowDiffLive3.__init__(self)
        self._base_file = base_file
        self._open_file(their_file, 0)
        self._merged_view = self._open_file(merged_file, 1)
        self._merged_view.get_view().set_scratch(False)
        self._open_file(mine_file, 2)
        self._run_diff_when_all_loaded()
        self.on("destroy", self._cleanup_after_merge)

    def _can_use_current_window(self):
        return False

    def is_2way(self):
        return False

    def is_3way(self):
        return True

    def save(self):
        self._layout.get_merged().get_view().run_command("save")
        BaseDiffWindow.save(self)

    def can_close(self):
        return BaseDiffWindow.can_close(self) and sublime.ok_cancel_dialog("Sublimerge\n\nDo you want to close the merge?", "Yes")

    def _initialize_diff_thread(self, views):
        return self.DiffThreadClass(self._base_file, *views)

    def _on_diff_change(self, sender, seq_number, change_their, change_base, change_mine):
        their = self._layout.get_left()
        mine = self._layout.get_right()
        their.get_lines().render_hunk(change_their)
        mine.get_lines().render_hunk(change_mine)

    def _on_diff_done(self, sender, view_their, view_mine, merged_text, merged_hunks):
        view_their.get_lines().prepare_to_flush()
        view_mine.get_lines().prepare_to_flush()
        return Promise.all([
         Task.spawn((lambda : view_their.get_lines().flush())),
         Task.spawn((lambda : view_mine.get_lines().flush())),
         Task.spawn((lambda : self._on_diff_merged(merged_text, merged_hunks)))])

    def _on_diff_merged(self, merged_text, merged_hunks):
        merged = self._layout.get_merged()
        lines = merged.get_lines()
        merged.get_view().run_command("sublimerge_view_replace", {"begin": 0, 
         "end": (merged.get_view().size()), 
         "text": merged_text})
        lines.initialize()
        for seq_number, change in enumerate(merged_hunks):
            lines.render_hunk(change)

        lines.flush()

    def _cleanup_after_merge(self, *args):
        try:
            if Settings.get("vcs_after_merge_cleanup"):
                console.log("Performing after-merge cleanup")
                path = self._merged_view.get_diff_file().get_original_path()
                VCS.merge_cleanup(path)
        except Exception as e:
            console.error("Failed after-merge cleanup", e)
