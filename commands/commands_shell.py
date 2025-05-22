import sublime, sublime_plugin
from os.path import exists, basename
from ..core.window.text.diff_window import DiffWindow2, DiffWindow3
from ..core.diff_file import CurrentLocalFile, LocalFile

class SublimergeDiffViewsCommand(sublime_plugin.WindowCommand):

    def run(self, **kwargs):
        views = sublime.active_window().views()
        if len(views) == 2:
            left_path = views[0].file_name()
            right_path = views[1].file_name()
            if not self._exists(left_path):
                return
            if not self._exists(right_path):
                return
            DiffWindow2.spawn(CurrentLocalFile(views[0], read_only=kwargs["left_read_only"] if "left_read_only" in kwargs else False), CurrentLocalFile(views[1], read_only=kwargs["right_read_only"] if "right_read_only" in kwargs else False), DiffWindow2.WINDOW_MODE_CURRENT)
        elif len(views) == 4:
            if not self._exists(views[0].file_name()):
                return
            else:
                if not self._exists(views[1].file_name()):
                    return
                if not self._exists(views[2].file_name()):
                    return
                return self._exists(views[3].file_name()) or None
            base_path = views[1].file_name()
            merged_path = views[3].file_name()
            file_name = basename(merged_path)
            DiffWindow3.spawn(CurrentLocalFile(views[0], read_only=True, title="Theirs: %s" % file_name, temporary=True), LocalFile(base_path, read_only=True, temporary=True), CurrentLocalFile(views[2], read_only=True, title="Mine: %s" % file_name, temporary=True), LocalFile(merged_path, read_only=False), DiffWindow3.WINDOW_MODE_CURRENT)

            def close():
                views[3].close()
                views[1].close()

            sublime.set_timeout(close, 1)
        else:
            self._error_message("Wrong number of files (%d). Expecting 2 or 4." % len(views))

    def _exists(self, path):
        if exists(path):
            return True
        self._error_message("File not found: " + path)
        return False

    def _error_message(self, msg):
        sublime.error_message("Sublimerge\n\n" + msg)
        sublime.active_window().run_command("close_window")
