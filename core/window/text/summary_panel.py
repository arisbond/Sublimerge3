import sublime
from ...lines.line import Line
from ...utils import icon_path
from ...settings import Settings
from ...diff.intralines import DiffIntralines
from ...renderers.groups_renderers import GutterRenderer, ICONS_GROUP_START_RIGHT, ICONS_GROUP_START_LEFT
from ...observable import Observable
from ...object import Object
from ...themer import Themer

class SummaryLine(Line):
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, view, lineno, change_type=Line.TYPE_CHANGE):
        Observable.__init__(self)
        if Object.DEBUG:
            Object.add(self)
        self._type = self.TYPE_EQUAL
        self._name = "line-%d" % lineno
        self._lineno = lineno
        self._view = view
        self._undo_redo_text = ""
        self._change_type = change_type
        self._owning_lines = None
        self._destroyed = False
        return


class DiffWindowSummaryPanel:
    PANEL_NAME = "summary-panel"
    FULL_PANEL_NAME = "output.summary-panel"
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_window):
        if Object.DEBUG:
            Object.add(self)
        self._diff_window = diff_window
        self._panel = diff_window.get_window().create_output_panel(self.PANEL_NAME)
        self._configured = False
        self._lines = []
        self._can_show = True
        self._intralines = None
        self._destroyed = False
        return

    def destroy(self):
        if self._destroyed:
            return
        self._diff_window.get_window().run_command("hide_panel", {"panel": (self.FULL_PANEL_NAME)})
        self._destroyed = True
        if self._intralines:
            self._intralines.destroy()
        while self._lines:
            self._lines.pop().destroy()

        Object.free(self)

    def on_show_panel(self, panel):
        self._can_show = False

    def on_hide_panel(self):
        if self._can_show:
            return ("noop", {})
        self._can_show = True
        sublime.set_timeout((lambda : self.refresh(self._diff_window.get_focused_view())), 10)

    def refresh(self, diff_view):
        if not Settings.get("summary_panel"):
            return
        if not self._configured:
            settings = {"word_wrap": True,  "highlight_line": False, 
             "draw_white_space": "all", 
             "scroll_past_end": False, 
             "line_numbers": False, 
             "__vi_external_disable": True, 
             "is_sublimerge_view": True, 
             "is_sublimerge_summary_panel": True, 
             "gutter": True, 
             "margin": (-8), 
             "line_numbers": False, 
             "color_scheme": (Themer.summary_panel_theme_file()), 
             "theme": (diff_view.get_view().settings().get("theme"))}
            for setting in settings:
                self._panel.settings().set(setting, settings[setting])

            self._configured = True
        ICONS_RIGHT = ICONS_GROUP_START_RIGHT.copy()
        ICONS_LEFT = ICONS_GROUP_START_LEFT.copy()
        ICONS_RIGHT.update({"dummy": "dummy"})
        ICONS_LEFT.update({"dummy": "dummy"})
        self._panel.set_read_only(False)
        sel = diff_view.get_view().sel()
        if len(sel) == 1:
            row, _ = diff_view.get_view().rowcol(sel[0].end())
            if self._intralines:
                self._intralines.destroy()
            for line in self._lines:
                line.destroy()

            self._lines = []
            self._panel.run_command("sublimerge_view_replace", {"begin": 0, 
             "end": (self._panel.size()), 
             "text": ""})
            views = self._diff_window.get_active_views()
            line1 = views[0].get_lines().get_line(row)
            line2 = views[-1].get_lines().get_line(row)
            if self._diff_window.is_2way() and line1.get_type() == line1.TYPE_MISSING and line2.get_type() == line2.TYPE_MISSING:
                sublime.set_timeout((lambda : self.refresh(diff_view)), 100)
                return
            lines = [line1, line2] if self._diff_window.is_2way() else [line1, views[1].get_lines().get_line(row), line2]
            self._panel.run_command("sublimerge_view_insert", {"begin": 0, 
             "text": ("\n".join([line.get_view_text() for line in lines]))})
            for i in range(len(lines)):
                point = self._panel.text_point(i, 0)
                region = self._panel.line(point)
                line = SummaryLine(self._panel, i, lines[i].get_change_type())
                line.set_type(lines[i].get_type())
                self._lines.append(line)

            GutterRenderer.render_line(self._panel, self._lines[0], 0, 0, ICONS_RIGHT)
            if self._diff_window.is_3way():
                GutterRenderer.render_line(self._panel, self._lines[1], 0, 0, ICONS_RIGHT if self._lines[1] == self._lines[0] else ICONS_LEFT)
            GutterRenderer.render_line(self._panel, self._lines[-1], 0, 0, ICONS_LEFT)
            self._intralines = DiffIntralines(self._lines[0], self._lines[-1])
            self._panel.set_read_only(True)
            if self._can_show:
                self._diff_window.get_window().run_command("show_panel", {"panel": (self.FULL_PANEL_NAME)})
