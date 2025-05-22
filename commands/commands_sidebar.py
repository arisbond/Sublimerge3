import sublime
from .base_commands import _BaseSidebarCommand
from ..core.utils import error_message

class SublimergeCompareSelectedFiles(_BaseSidebarCommand):

    def description(self, files=[], paths=[]):
        if self._did_select_files(files, paths):
            return "Compare Selected Files"
        if self._did_select_dirs(files, paths):
            return "Compare Selected Directories"
        return "Compare Selected"

    def is_enabled(self, files=[], paths=[]):
        return True

    def is_visible(self, files=[], paths=[]):
        return True

    def run(self, files=[], paths=[]):
        if not self._did_select_comparable(files, paths):
            error_message("Please select two files or directories to compare.")
            return
        self.window.run_command("sublimerge_compare_paths", {"paths": paths})
