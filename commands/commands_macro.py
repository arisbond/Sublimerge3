import sublime, sublime_plugin
from .base_commands import _BaseEditorCommand
from ..core.menu import Menu, MenuItem
from ..core.macros import Macros
from ..core.utils import sort
from ..core.settings import Settings

class SublimergeMacroCommand(_BaseEditorCommand):

    def description(self, run=-1):
        if run >= 0:
            macros = Macros.get_macros()
            if len(macros) > 0:
                return macros[run].description()
        return "Run Macro..."

    @staticmethod
    def is_visible_in_menu():
        return Settings.get("macros_in_separate_menu")

    def is_visible(self, run=-1):
        if run >= 0:
            macros = Macros.get_macros()
            return len(macros) > 0 and macros[run].is_visible()
        else:
            return any([m.is_visible() and m.is_enabled() for m in Macros.get_macros()])
        return True

    def is_enabled(self, run=-1):
        return self.is_visible(run)

    def run(self, run=-1):
        macros = Macros.get_macros(True)
        if run >= 0 and len(macros) > 0:
            macros[run].execute()
        else:
            menu = Menu(on_select=self._on_select)

            def sorter(a, b):
                if a.description() < b.description():
                    return -1
                if a.description() > b.description():
                    return 1
                return 0

            def find_unsorted_index(m, macros):
                for i, m2 in enumerate(macros):
                    if m is m2:
                        return i

            for m in sort(macros, sorter):
                if m.is_enabled():
                    menu.add_item(MenuItem(caption=m.description(), value=find_unsorted_index(m, macros)))
                    continue

            menu.show()

    def _on_select(self, sender, item):
        sublime.active_window().run_command("sublimerge_macro", {"run": (item.get_value())})
