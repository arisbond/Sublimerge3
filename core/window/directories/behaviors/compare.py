import sublime, os
from ....utils import error_message, is_binary
from ....settings import Settings
from ...text.diff_window import DiffWindowTextInDirectories, DiffWindow2
from ....diff_file import LocalFile

class CompareBehavior:

    def __init__(self):
        self._current_diff = None
        return

    def destroy(self):
        if self._current_diff:
            self._current_diff.reject()

    def _compare_node(self, node):
        if is_binary(node.left.path) or is_binary(node.right.path):
            error_message("Binary files can't be compared.")
            return
        else:
            if Settings.get("dir_compare_open_text_diff_in_new_window"):
                WindowClass = DiffWindow2
                window_mode = DiffWindow2.WINDOW_MODE_NEW
            else:
                WindowClass = DiffWindowTextInDirectories
                window_mode = DiffWindowTextInDirectories.WINDOW_MODE_CURRENT
            if self._current_diff:
                self._current_diff.reject()
            self._current_diff = WindowClass.spawn(LocalFile(node.left.path, read_only=not bool(node.left.path), title=os.path.basename(node.right.path) + " <missing>" if not node.left.path else None), LocalFile(node.right.path, read_only=not bool(node.right.path), title=os.path.basename(node.left.path) + " <missing>" if not node.right.path else None), window_mode).then((lambda : self._listing.refresh(node=node)))
            return
