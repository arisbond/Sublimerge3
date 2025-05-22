import sublime, sublime_plugin, sys, os
from ..core.metadata import PROJECT_NAME
from ..core.menu import Menu, MenuItem
from ..core.vcs.vcs import VCS
from ..core.linsp import LInsp
from ..core.settings import Settings
from .base_commands import _BaseEditorCommand
from .commands_editor import *
from .commands_vcs import *
from .commands_snapshots import *
from .commands_macro import *
from .commands_sidebar import *

def sort_items(a, b):
    if isinstance(a.get_value()[0], SublimergeCompareToViewCommand):
        return -1
    if a.get_caption() == "Run Macro...":
        return 1
    if b.get_caption() == "Run Macro...":
        return -1
    a7 = a.get_caption()[0:7]
    b7 = b.get_caption()[0:7]
    if a7 == "Compare" and a7 == b7:
        a10 = a.get_caption()[0:10]
        b10 = b.get_caption()[0:10]
        if a10 == b10:
            if a.get_caption() > b.get_caption():
                return -1
            else:
                return 1
        else:
            if a10 == "Compare to":
                return -1
            else:
                return 1
    else:
        if a7 == "Compare":
            return -1
        else:
            if b7 == "Compare":
                return 1
            return (a.get_caption() > b.get_caption()) - (a.get_caption() < b.get_caption())


class SublimergeCommand(_BaseEditorCommand):

    def __init__(self, *args):
        _BaseEditorCommand.__init__(self, *args)
        if not self.is_context():
            return
        self._commands = []
        for name in dir(sys.modules[PROJECT_NAME + ".commands.commands_sublimerge"]):
            if not name.startswith("_") and name.endswith("Command") and name != "SublimergeCommand":
                CmdClass = getattr(sys.modules[PROJECT_NAME + ".commands.commands_sublimerge"], name)
                if hasattr(CmdClass, "is_visible_in_menu"):
                    if CmdClass.is_visible_in_menu():
                        self._commands.append((CmdClass(self.window), {}))
                continue

        if not Settings.get("macros_in_separate_menu"):
            for i, m in enumerate(Macros.get_macros(True)):
                self._commands.append((SublimergeMacroCommand(self.window), {"run": i}))

    def run(self):
        if not LInsp.r_rem():
            menu = Menu(items=[MenuItem(caption=cmd.description(**args), value=(cmd, args)) for cmd, args in self._commands if cmd.is_visible(**args) and cmd.is_enabled(**args)], on_select=(lambda sender, item: (
             item.get_value()[0].run(**item.get_value()[1]), sender.destroy())), on_cancel=(lambda sender: sender.destroy()), sorter=sort_items)
            menu.show()


class SublimergePurgeVcsCacheCommand(sublime_plugin.WindowCommand):

    def description(self):
        return "Purge VCS Cache"

    def run(self):
        VCS.purge()
        sublime.message_dialog("Sublimerge\n\nVersions Control Systems cache purged!")


class SublimergeValidateVcsCacheCommand(sublime_plugin.WindowCommand):

    def description(self):
        return "Validate VCS Cache"

    def run(self):
        VCS.validate().then((lambda *args: sublime.message_dialog("Sublimerge\n\nVersion Control Systems cache validated!")))


class SublimergeViewVcsCacheCommand(sublime_plugin.WindowCommand):

    def description(self):
        return "View VCS Cache"

    def is_visible(self):
        return os.path.exists(os.path.join(sublime.cache_path(), VCS.CACHE_FILE_NAME))

    def is_enabled(self):
        return self.is_visible()

    def run(self):
        self.window.open_file(os.path.join(sublime.cache_path(), VCS.CACHE_FILE_NAME))
