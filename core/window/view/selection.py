import sublime, time
from ...utils import subtract_regions
from ...object import Object

class DiffViewSelection:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_view):
        if Object.DEBUG:
            Object.add(self)
        self._diff_view = diff_view
        self._handling = False
        self._previous = None
        self._text_regions_cache = None
        return

    def _unpack(self):
        view = self._diff_view.get_view()
        selection = view.sel()
        view_size = view.size()
        return (
         view, selection, view_size)

    def on_selection_modified(self):
        if not self._diff_view.is_focused() or self._handling:
            return
        self._handling = True
        view, selection, view_size = self._unpack()
        if len(selection) > 1:
            for sel in selection:
                if sel != self._previous:
                    selection.clear()
                    selection.add(sel)
                    break

        if len(selection) > 0:
            self._previous = selection[0]
        self._handling = False

    def destroy(self):
        Object.free(self)
