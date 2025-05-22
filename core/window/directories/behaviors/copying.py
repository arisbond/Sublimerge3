import sublime, os
from ....utils import error_message
from ....task import Task
from ..file_ops import FileOps

class CopyingBehavior:

    def __init__(self):
        self._is_processing = False

    def copy_file(self, source, target):
        if self._is_processing:
            error_message("Please wait for current operations to finish.")
            return
        else:
            source, target = (target, source) if self._swapped else (source, target)
            node = self._listing.get_selected_node()
            sides = [
             node.left_path, node.right_path]
            source_path = sides[source]
            target_path = sides[target]
            sides = [
             node.left, node.right]
            source_file = sides[source].name or None
            target_file = sides[target].name or None
            if not self._confirm_copying(source_file, target_file, source_path, target_path):
                return
            self._is_processing = True
            ops = FileOps()
            Task.spawn(ops.run, [
             (
              source_file, target_file)], (
             source_path, target_path), (lambda progress: self._set_status("percent", "%d%%" % progress))).progress("Applying...").then((lambda *args: self._finished_copying(node, source_file, target_file)))
            return

    def _finished_copying(self, node, source_file, target_file):
        try:
            node.set_type(None)
            self._set_status("percent", None)
            self._is_processing = False
            if source_file is not None:
                self._listing.refresh(node)
            else:
                self._listing.remove(node)
            self.select_current_change()
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            print("at node", node)

        return

    def _confirm_copying(self, source_file, target_file, source_path, target_path):
        if source_file is None:
            return sublime.ok_cancel_dialog("Delete:\n\n%s\n\nThis operation cannot be undone!\nContinue?" % os.path.join(target_path, target_file))
        else:
            if target_file is None:
                return True
            return sublime.ok_cancel_dialog("Overwrite:\n\n%s\n\nThis operation cannot be undone!\nContinue?" % os.path.join(target_path, target_file))
