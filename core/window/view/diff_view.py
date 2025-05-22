import sublime, datetime, os
from ...observable import Observable
from ...diff_file import LocalFile
from ...promise import Promise
from ...utils import subtract_regions
from ...lines.lines_collection import LinesCollection
from ...debug import console
from ...object import Object
from ...settings import Settings
from ...themer import Themer
from .collection import DiffViewCollection
from .loader import DiffViewLoader
from .selection import DiffViewSelection

class DiffView(Observable):
    EVENTS = [
        'destroy', 'load', 'focus', 'blur', 'activate', 'deactivate', 
        'modified', 'pre_save', 'post_save', 'selection_modified', 'scroll', 
        'scroll_stop', 'resize'
    ]
    DEFAULTS = {
        "scroll_past_end": False,
        "word_wrap": False,
        "draw_white_space": "all",
        "draw_indent_guides": True,
        "indent_guide_options": ["draw_normal", "draw_active"],
        "save_on_focus_lost": False,
        "highlight_line": True,
        "line_numbers": False,
        "fold_buttons": False,
        "show_line_endings": True,
        "show_encoding": True,
        "drag_text": False,
        "scroll_speed": 0,
        "detect_indentation": False,
        "__vi_external_disable": True,
        "is_sublimerge_view": True,
        "translate_tabs_to_spaces": False,
        "trim_trailing_white_space_on_save": False,
        "ensure_newline_at_eof_on_save": False
    }

    if Object.DEBUG:
        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_window, diff_file=None, view=None):
        if Object.DEBUG:
            Object.add(self)
        Observable.__init__(self)
        self._view = None
        self._is_active = False
        self._diff_window = diff_window
        self._window = diff_window.get_window()
        self._destroyed = False
        self._regions = {}
        self._handling_modified = False
        self._group = None
        self._is_read_only = diff_file.is_read_only() if diff_file is not None else False
        self._text = None
        self._is_loaded = False
        self._diff_regions = {}
        self._seq_number = 0
        self._focused = False
        self._diff_file = diff_file
        self._loader = DiffViewLoader()
        self._scroll_to_promise = None
        self._can_continue_save = True
        self._last_size = None
        self._is_modifyable = None
        self._view, self._diff_file, self._loaded_promise = self._loader.load(diff_file, diff_window, view)
        self._view.set_read_only(True)
        self._selection = DiffViewSelection(self)
        if self._diff_file:
            self._lines = LinesCollection(self)
        view_settings = Settings.get("view")
        for setting in self.DEFAULTS:
            self._view.settings().set(setting, view_settings[setting] if setting in view_settings else self.DEFAULTS[setting])

        self._view.settings().set("color_scheme", Themer.diff_view_theme_file())
        DiffViewCollection.add(self)
        if diff_file:
            self._loaded_promise.then((lambda *result: self.on_load()))
        self._watch_size()
        self.on("selection_modified", (lambda sender, *args: self._selection.on_selection_modified()))

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        if self._scroll_to_promise:
            self._scroll_to_promise.reject()
        self.fire("destroy")
        self.un()
        if self._diff_file is not None:
            self._diff_file.destroy()
            self._lines.destroy()
        self._loader.destroy()
        DiffViewCollection.remove(self)
        Object.free(self)

    def is_modifyable(self):
        if self._is_modifyable is None:
            return not self.is_read_only()
        return self._is_modifyable

    def set_modifyable(self, modifyable):
        self._is_modifyable = modifyable

    def _watch_size(self):
        if self._destroyed:
            return
        size = self._view.viewport_extent()
        if size != self._last_size:
            self._last_size = size
            self.fire("resize", self._view.visible_region())
        sublime.set_timeout(self._watch_size, 100)

    def is_destroyed(self):
        return self._destroyed

    def __eq__(self, other):
        return self._view.id() == (other and other.get_view() and other.get_view().id())

    def reset(self):
        self._lines.reset()

    def scroll_to(self, region):
        visible = self._view.visible_region()
        viewport_layout_begin = self._view.text_to_layout(visible.begin())[1]
        viewport_layout_end = self._view.text_to_layout(visible.end())[1]
        viewport_layout_height = viewport_layout_end - viewport_layout_begin
        line_height = self._view.line_height()
        region_layout_begin = self._view.text_to_layout(region.begin())[1] - line_height
        region_layout_end = self._view.text_to_layout(region.end())[1] + line_height
        region_layout_height = region_layout_end - region_layout_begin
        begins_before_viewport = region_layout_begin < viewport_layout_begin
        ends_before_viewport = region_layout_end < viewport_layout_begin
        begins_after_viewport = region_layout_begin > viewport_layout_end
        ends_after_viewport = region_layout_end > viewport_layout_end
        viewport_position = self._view.viewport_position()
        if self._scroll_to_promise:
            self._scroll_to_promise.reject()
        self._scroll_to_promise = Promise().then((lambda : self.on_scroll_stop(self._view.visible_region())))
        if region_layout_height > viewport_layout_height or region_layout_height > viewport_layout_height / 2:
            self._view.set_viewport_position((viewport_position[0], region_layout_begin), True)
            sublime.set_timeout(self._scroll_to_promise.resolve, 200)
            return
        if begins_after_viewport:
            self._view.set_viewport_position((viewport_position[0], region_layout_begin), True)
        elif ends_before_viewport:
            self._view.set_viewport_position((viewport_position[0], region_layout_begin - viewport_layout_height + region_layout_height), True)
        elif ends_after_viewport:
            self._view.set_viewport_position((viewport_position[0], viewport_position[1] + (region_layout_end - viewport_layout_end)), True)
        elif begins_before_viewport:
            self._view.set_viewport_position((viewport_position[0], viewport_position[1] + (region_layout_begin - viewport_layout_begin)), True)
        sublime.set_timeout(self._scroll_to_promise.resolve, 200)

    def get_diff_file(self):
        return self._diff_file

    def get_lines(self):
        return self._lines

    def get_change(self, index):
        return self._lines.get_group(index)

    def get_changes(self):
        return self._lines.get_groups()

    def get_window(self):
        return self._diff_window

    def move_caret_to(self, row, col):
        point = self._view.text_point(row, max(col, 0))
        if col < 0:
            point = self._view.line(point).end() + col + 1
        self._view.sel().clear()
        self._view.sel().add(sublime.Region(point, point))
        self.fire("selection_modified")

    def set_read_only(self, read_only):
        self._is_read_only = read_only

    def apply_read_only(self):
        self._view.set_read_only(self.is_read_only())

    def set_group(self, group):
        self._group = group

    def get_group(self):
        return self._group

    def get_text(self):
        return self._lines.get_text()

    def get_diff_regions(self):
        return self._diff_regions.values()

    def get_view(self):
        return self._view

    def is_loaded(self):
        return self._loaded_promise.is_resolved()

    def is_read_only(self):
        if self._diff_file is not None:
            return self._diff_file.is_read_only()
        return self._is_read_only

    def get_loaded_promise(self):
        return self._loaded_promise

    def on_close(self):
        self.destroy()

    def on_load(self):
        if self._diff_file:
            if self.is_read_only():
                self._view.set_name(self._diff_file.get_title() + " (read-only)")
            elif self._diff_file and not self._diff_file.get_path():
                self._view.set_name(self._diff_file.get_title())
            self._lines.initialize()
        self._is_loaded = True

    def on_scroll(self, visible_region):
        self.fire("scroll", visible_region)

    def on_scroll_stop(self, visible_region):
        self.fire("scroll_stop", visible_region)

    def on_focus(self):
        self._focused = True
        self.fire("focus")

    def on_blur(self):
        self._focused = False
        self.fire("blur")

    def is_focused(self):
        return self._focused

    def focus(self):
        if self._group:
            self._group.focus_view(self)

    def on_modified(self):
        if not self._is_loaded or self._handling_modified:
            return
        self._handling_modified = True
        self._view.set_scratch(False)
        self.fire("modified")
        self._handling_modified = False

    def on_selection_modified(self):
        if not self.is_loaded():
            return
        self.fire("selection_modified")

    def on_pre_save(self):
        self.fire("pre_save")

    def on_post_save(self):
        if self._can_continue_save:
            self._diff_file.save(self)
            self.fire("post_save")

    cm = False

    def on_context_menu(self, args):
        if not self.cm:
            self.cm = True
            self._view.run_command("drag_select", {"event": args["event"]})
            self._view.run_command("drag_select", {"event": args["event"]})

            def un_cm():
                self.cm = False

            def op():
                sublime.set_timeout_async(un_cm, 150)
                self._view.run_command("context_menu", args)

            sublime.set_timeout_async(op, 200)
            return False
        self.cm = False
        return True
