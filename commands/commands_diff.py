import sublime_plugin
from ..core.settings import Settings
from .base_commands import _BaseDiffCommand
from .commands_text import *

class SublimergeShowChangesNavigator(_BaseDiffCommand):

    def run(self):
        self._window.show_changes_navigator()


class SublimergeRecompareCommand(_BaseDiffCommand):

    def run(self):
        self._window.refresh()

    def is_allowed_in_dirs_view(self):
        return False

    def is_visible(self):
        return _BaseDiffCommand.is_visible(self) and self._window.is_2way()

    def description(self):
        return "Recompare Buffers"


class SublimergeSaveCommand(_BaseDiffCommand):

    def run(self):
        self._window.save()

    def is_allowed_in_dirs_view(self):
        return False

    def is_visible(self):
        return False

    def is_enabled(self):
        return self.is_context()


class SublimergeSwapViewCommand(_BaseDiffCommand):

    def is_allowed_in_dirs_view(self):
        return False

    def run(self):
        self._window.get_layout().swap()

    def description(self):
        return "Swap View"


class SublimergeGoUpCommand(_BaseDiffCommand):

    def run(self, change_only=False):
        self._window.select_previous_change(change_only)

    def is_allowed_in_dirs_view(self, *args):
        return True

    def is_enabled(self, change_only=False):
        return _BaseDiffCommand.is_enabled(self) and self._window.get_previous_change(change_only) is not None

    def description(self):
        return "Previous Change"


class SublimergeGoDownCommand(_BaseDiffCommand):

    def run(self, change_only=False):
        self._window.select_next_change(change_only)

    def is_allowed_in_dirs_view(self, *args):
        return True

    def is_enabled(self, change_only=False):
        return _BaseDiffCommand.is_enabled(self) and self._window.get_next_change(change_only) is not None

    def description(self):
        return "Next Change"


class SublimergeGoIntoCommand(_BaseDiffCommand):

    def run(self):
        self._window.go_into_selected_change()

    def is_allowed_in_dirs_view(self, *args):
        return True

    def is_enabled(self):
        return _BaseDiffCommand.is_enabled(self) and self._window.get_selected_change() is not None

    def description(self):
        return "Go Into"


class SublimergeGoBackCommand(_BaseDiffCommand):

    def run(self):
        self._window.go_back()

    def is_allowed_in_dirs_view(self, *args):
        return True

    def is_enabled(self):
        return _BaseDiffCommand.is_enabled(self)

    def description(self):
        return "Go Back"


class SublimergeCopyCommand(_BaseDiffCommand):
    LEFT_TO_RIGHT = [
     0, -1]
    RIGHT_TO_LEFT = [-1, 0]

    def is_allowed_in_dirs_view(self, direction, subject="section_or_line", action="replace"):
        return subject == "file"

    def is_allowed_in_text_view(self, direction, subject="section_or_line", action="replace"):
        return subject != "file"

    def run(self, direction, subject="section_or_line", action="replace"):
        source, target = direction if action == "use_both" else self._prepare_direction(direction)
        if subject == "section_or_line" or subject == "section":
            is_selected = self._window.get_selected_change()
            if not is_selected:
                if subject == "section":
                    self._window.set_selected_change(self._window._find_change_under_caret())
                    is_selected = self._window.get_selected_change()
            if action == "replace":
                if is_selected:
                    self._window.copy_selected_change(source, target)
                else:
                    self._window.copy_single_line(source, target)
            elif action == "use_both":
                if is_selected:
                    self._window.copy_selected_change_both(source, target)
                else:
                    self._window.copy_single_line_after(source, target)
        elif subject == "line":
            if action == "replace":
                self._window.copy_single_line(source, target)
            elif action == "use_both":
                self._window.copy_single_line_after(source, target)
        elif subject == "all":
            self._window.copy_all_changes(source, target)
        elif subject == "file":
            self._window.copy_file(source, target)

    def is_enabled(self, direction, subject="section_or_line", action="replace"):
        if self.is_context():
            source, target = self._prepare_direction(direction)
            views = self._window.get_active_views()
            enabled = _BaseDiffCommand.is_visible(self, direction, subject, action) and self._window.get_active_views()[target].is_modifyable()
            if enabled:
                if self.is_dirs_view() and not self.is_allowed_in_dirs_view(direction, subject, action):
                    return False
                else:
                    if self.is_text_view() and not self.is_allowed_in_text_view(direction, subject, action):
                        return False
                    else:
                        if action == "use_both":
                            if not self._window.is_3way():
                                return False
                        if subject == "section_or_line":
                            return self._window.get_selected_change() is not None or self._window.can_copy_single_line(source, target)
                        if subject == "section":
                            return self._window._find_change_under_caret() is not None
                        if subject == "line":
                            pass
                        return self._window.can_copy_single_line(source, target)
                    if subject == "file":
                        pass
                    return self._window.get_selected_change() is not None
            return enabled
        else:
            return False

    def is_visible(self, direction, subject="section_or_line", action="replace"):
        if self.is_context():
            source, target = self._prepare_direction(direction)
            views = self._window.get_active_views()
            return _BaseDiffCommand.is_visible(self, direction, subject, action) and (self.is_text_view() and self.is_allowed_in_text_view(direction, subject, action) and (self._window.is_2way() and action != "use_both" and views[source] == self._window.get_focused_view() or self._window.is_3way() and self._window.get_focused_view() in [self._window.get_layout().get_merged(), views[source]]) or self.is_dirs_view() and self.is_allowed_in_dirs_view(direction, subject, action) and views[source] == self._window.get_focused_view())
        return False

    def description(self, direction, subject="section_or_line", action="replace"):
        if self.is_context():
            source, target = direction
            is_2way = self._window.is_2way()
            is_merged_focused = not is_2way and self._window.get_focused_view() is self._window.get_layout().get_merged()
            subject_to_text = {"replace": [
                         {"section": ("Copy Change to Left" if is_2way else "Use Right Change" if is_merged_focused else "Use This Change"), 
                          "line": ("Copy Line to Left " if is_2way else "Use Right Line" if is_merged_focused else "Use This Line"), 
                          "all": ("Copy All to Left" if is_2way else "Use Right Side" if is_merged_focused else "Use This Side"), 
                          "file": "Copy File to Left"},
                         {"section": ("Copy Change to Right" if is_2way else "Use Left Change" if is_merged_focused else "Use This Change"), 
                          "line": ("Copy Line to Right" if is_2way else "Use Left Line" if is_merged_focused else "Use This Line"), 
                          "all": ("Copy All to Right" if is_2way else "Use Left Side" if is_merged_focused else "Use This Side"), 
                          "file": "Copy File to Right"}], 
             "use_both": [
                          {"section": ("Copy Right Change before Left" if is_2way else "Use Right Change before Left" if is_merged_focused else "Use This Change before Left"), 
                           "line": ("Copy Right Line before Left" if is_2way else "Use Right Line before Left" if is_merged_focused else "Use This Line before Left")},
                          {"section": ("Copy Left Change before Right" if is_2way else "Use Left Change before Right" if is_merged_focused else "Use This Change before Right"), 
                           "line": ("Copy Left Line before Right" if is_2way else "Use Left Line before Right" if is_merged_focused else "Use This Line before Left")}]}
            return subject_to_text[action][target][subject]
        return ""

    def _prepare_direction(self, direction):
        if self._window.is_2way():
            return direction
        return (direction[0], 1)


class SublimergeToggleSettingCommand(_BaseDiffCommand):
    IGNORE_WHITESPACE = "ignore_whitespace"
    IGNORE_CRLF = "ignore_crlf"
    IGNORE_CASE = "ignore_case"
    INTRALINE_ANALYSIS = "intraline_analysis"
    THREE_WAY_NAVIGATE_ALL = "three_way_navigate_all"
    VISIBLE_2_WAY = [
     IGNORE_WHITESPACE,
     IGNORE_CRLF,
     IGNORE_CASE,
     INTRALINE_ANALYSIS]
    VISIBLE_3_WAY = [
     INTRALINE_ANALYSIS,
     THREE_WAY_NAVIGATE_ALL]
    NEED_DIFF_REFRESH = [
     IGNORE_WHITESPACE,
     IGNORE_CRLF,
     IGNORE_CASE]
    NEED_STATUS_REFRESH = [
     INTRALINE_ANALYSIS]
    DESCRIPTIONS = {(IGNORE_WHITESPACE + ".begin"): "Ignore Whitespace: Line Begin", 
     (IGNORE_WHITESPACE + ".middle"): "Ignore Whitespace: Line Middle", 
     (IGNORE_WHITESPACE + ".end"): "Ignore Whitespace: Line End", 
     IGNORE_CRLF: "Ignore CR/LF", 
     IGNORE_CASE: "Ignore Case", 
     INTRALINE_ANALYSIS: "Intraline Analysis", 
     THREE_WAY_NAVIGATE_ALL: "Navigate Through All Changes"}

    def run(self, setting, value=None):
        current = Settings.get(setting)
        if value is None:
            Settings.set(setting, not current)
            value = not current
        elif value in current:
            current.remove(value)
        else:
            current.append(value)
        Settings.set(setting, current)
        value = current
        if setting in self.NEED_DIFF_REFRESH:
            self._window.refresh()
        if setting in self.NEED_STATUS_REFRESH:
            self._window.refresh_status()
        if setting == self.INTRALINE_ANALYSIS:
            if value:
                self._window.highlight_intraline_changes()
            else:
                self._window.remove_intraline_changes()
        return

    def is_enabled(self, setting, value=None):
        return self.is_visible(setting, value)

    def is_checked(self, setting, value=None):
        current = Settings.get(setting)
        if value is None:
            return current
        else:
            return value in current

    def is_visible(self, setting, value=None):
        if self.is_context():
            if not self._view.get_view().settings().get("is_sublimerge_dirs_view", False):
                if self._window.is_2way():
                    return setting in self.VISIBLE_2_WAY
                if self._window.is_3way():
                    return setting in self.VISIBLE_3_WAY
            return False

    def description(self, setting, value=None):
        key = [setting]
        if value is not None:
            key.append(value)
        return self.DESCRIPTIONS[".".join(key)]
