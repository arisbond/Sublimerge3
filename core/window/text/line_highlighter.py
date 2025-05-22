import sublime
from ...object import Object

class LineHighlighter:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_window):
        if Object.DEBUG:
            Object.add(self)
        self._layout = diff_window.get_layout()
        self._handling = False
        self._last_sel_rows = None
        self._any_panel_visible = False
        self._destroyed = False
        return

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        Object.free(self)

    def highlight(self, view, force=False):
        if self._destroyed or self._handling or view is not self._layout.get_focused_view():
            return
        self._handling = True
        self._highlight(view, force)

    def on_show_panel(self):
        self._any_panel_visible = True

    def on_hide_panel(self):
        self._any_panel_visible = False

    def _highlight(self, view, force):
        sel_rows = [view.get_view().rowcol(sel.end())[0] for sel in view.get_view().sel() if sel.empty()]
        if not self._any_panel_visible:
            if force or sel_rows != self._last_sel_rows:
                self._last_sel_rows = sel_rows
                for other in self._layout.get_active_views():
                    if not other is view:
                        if not other:
                            continue
                        other.set_silent("focus", True)
                        other.set_silent("selection_modified", True)
                        other.get_view().sel().clear()
                        for row in sel_rows:
                            other.get_view().sel().add(other.get_view().text_point(row, 0))

                        other.focus()
                        other.set_silent("focus", False)
                        other.set_silent("selection_modified", False)

                view.set_silent("focus", True)
                view.set_silent("selection_modified", True)
                view.focus()
                view.set_silent("focus", False)
                view.set_silent("selection_modified", False)
        self._handling = False
