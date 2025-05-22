import sublime
from .base_commands import _BaseEditorCommand
from ..core.snapshots import Snapshots
from ..core.utils import is_view_comparable
from ..core.menu import Menu, MenuItem
from ..core.settings import Settings
from ..core.window.text.diff_window import DiffWindow2
from ..core.diff_file import SnapshotFile, ViewFile

class _BaseSnapshotCommand(_BaseEditorCommand):

    @staticmethod
    def is_visible_in_menu():
        return Settings.get("snapshots_in_menu")

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        if not is_view_comparable(view):
            return False
        return _BaseEditorCommand.is_visible(self)

    def _menu(self, items, on_select):
        menu = Menu(on_select=(lambda sender, item: on_select(item.get_value())))
        for item in items:
            menu.add_item(MenuItem(caption=[
             item[0], "%s @ %s" % (item[2][:10], item[1])], value=item[2]))

        menu.show()


class SublimergeCompareToSnapshotCommand(_BaseSnapshotCommand):

    def description(self, index=-1, group=-1):
        return "Compare to Snapshot..."

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        return _BaseEditorCommand.is_visible(self) and Snapshots.has_any(view)

    def run(self, index=-1, group=-1):
        view = self._get_view(index, group)
        self._menu(Snapshots.get_menu_items(view, True), (lambda hash: self._compare(view, hash)))

    def _compare(self, view, hash):
        DiffWindow2.spawn(SnapshotFile(view=view, snapshot=Snapshots.get(view, hash)), ViewFile(view=view))


class SublimergeTakeSnapshotCommand(_BaseSnapshotCommand):

    def description(self, index=-1, group=-1):
        return "Snapshot: Create"

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        return _BaseSnapshotCommand.is_visible(self, index, group) and not Snapshots.exists(view)

    def run(self, index=-1, group=-1):
        view = self._get_view(index, group)
        self.window.show_input_panel("Enter Snapshot name:", Snapshots.get_next_name(), (lambda name: Snapshots.create(view, name)), None, None)
        return


class SublimergeReplaceSnapshotCommand(_BaseSnapshotCommand):

    def description(self):
        return "Snapshot: Replace..."

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        return _BaseSnapshotCommand.is_visible(self, index, group) and Snapshots.has_other_than(view)

    def run(self, index=-1, group=-1):
        view = self._get_view(index, group)
        self._menu(Snapshots.get_menu_items(view), (lambda hash: Snapshots.replace(view, hash)))


class SublimergeRemoveSnapshotCommand(_BaseSnapshotCommand):

    def description(self):
        return "Snapshot: Remove..."

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        return _BaseSnapshotCommand.is_visible(self, index, group) and (Snapshots.exists(view) or Snapshots.has_other_than(view))

    def run(self, index=-1, group=-1):
        view = self._get_view(index, group)
        self._menu(Snapshots.get_menu_items(view, True), (lambda hash: Snapshots.remove(view, hash)))


class SublimergeRestoreSnapshotCommand(_BaseSnapshotCommand):

    def description(self):
        return "Snapshot: Restore..."

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        return _BaseSnapshotCommand.is_visible(self, index, group) and Snapshots.has_other_than(view)

    def run(self, index=-1, group=-1):
        view = self._get_view(index, group)
        self._menu(Snapshots.get_menu_items(view), (lambda hash: Snapshots.restore(view, hash)))
