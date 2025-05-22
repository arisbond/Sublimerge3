import sublime
from .utils import sort

class MenuItem:

    def __init__(self, caption, value=None, selected=False, on_select=None, on_over=None, on_out=None):
        self._caption = caption
        self._on_select = on_select
        self._on_over = on_over
        self._on_out = on_out
        self._selected = selected
        self._value = value

    def get_value(self):
        return self._value

    def get_caption(self):
        return self._caption

    def get_selected(self):
        return self._selected

    def on_select(self):
        if self._on_select:
            self._on_select(self)

    def on_over(self):
        if self._on_over:
            self._on_over(self)

    def on_out(self):
        if self._on_out:
            self._on_out(self)


class Menu:

    def __init__(self, items=None, on_select=None, on_over=None, on_out=None, on_cancel=None, sorter=None):
        self._items = items or []
        self._selected = False
        self._current_over = None
        self._on_cancel = on_cancel
        self._on_select = on_select
        self._on_over = on_over
        self._on_out = on_out
        self._sorter = sorter
        return

    def add_item(self, item):
        self._items.append(item)

    def show(self):
        self._selected = False
        qp_items = []
        selected_index = -1
        if self._sorter:
            self._items = sort(self._items, self._sorter)
        for i, item in enumerate(self._items):
            if item.get_selected():
                selected_index = i
            qp_items.append(item.get_caption())

        sublime.set_timeout((lambda : sublime.active_window().show_quick_panel(qp_items, on_select=self._on_select_cb, on_highlight=self._on_over_cb, selected_index=selected_index)), 10)

    def destroy(self):
        self._items = []
        self._selected = False

    def _on_select_cb(self, index):
        if not self._selected:
            if index >= 0:
                self._items[index].on_select()
                if self._on_select:
                    self._on_select(self, self._items[index])
                self._selected = True
            elif self._current_over:
                self._current_over.on_out()
                if self._on_out:
                    self._on_out(self, self._current_over)
            if self._on_cancel:
                self._on_cancel(self)

    def _on_over_cb(self, index):
        if index >= 0:
            if self._current_over:
                self._current_over.on_out()
                if self._on_out:
                    self._on_out(self, self._current_over)
            self._current_over = self._items[index]
            self._current_over.on_over()
            if self._on_over:
                self._on_over(self, self._current_over)
