import sublime, sys

class Splitter:
    _indices = None
    _window = None
    _prev_layout = None
    _active_group = None
    _active_views_in_groups = None
    _sidebar_visible = False
    _should_hide_sidebar = False

    def restore(self):
        self._window = sublime.active_window()
        self._window.set_layout(self._window.settings().get("__layout_to_restore__"))
        self._window.settings().erase("__layout_to_restore__")
        for indice in reversed(self._indices):
            self._window.set_view_index(indice[0], indice[1][0], 0)

        for group in self._active_views_in_groups:
            self._window.focus_group(group)
            self._window.focus_view(self._active_views_in_groups[group])

        for view in self._window.views():
            if view.settings().get("is_sublimerge_view"):
                view.close()
                continue

        self._window.focus_group(self._active_group)
        self._should_hide_sidebar = False
        if self._sidebar_visible:
            self._window.set_sidebar_visible(self._sidebar_visible)

    def _hide_side_bar(self):

        def inner():
            if self._should_hide_sidebar:
                if self._window.is_sidebar_visible():
                    self._window.set_sidebar_visible(False)
                self._hide_side_bar()

        sublime.set_timeout_async(inner, 200)

    def split(self):
        self._window = sublime.active_window()
        self._indices = []
        self._active_group = self._window.active_group()
        self._active_views_in_groups = {}
        self._sidebar_visible = self._window.is_sidebar_visible()
        self._should_hide_sidebar = True
        self._window.settings().set("__layout_to_restore__", self._window.layout())
        self._window.settings().set("__is_sidebar_visible__", self._sidebar_visible)
        if self._sidebar_visible:
            self._hide_side_bar()
        for i in range(0, self._window.num_groups()):
            self._active_views_in_groups.update({i: (self._window.active_view_in_group(i))})

        self._window.set_layout({"cols": [
                  0.0, 0.5, 1.0], 
         "rows": [
                  0.0, 0.0, 1.0], 
         "cells": [
                   [
                    0, 1, 1, 2], [1, 1, 2, 2], [0, 0, 2, 1]]})
        for view in self._window.views():
            self._indices.append((view, self._window.get_view_index(view)))
            self._window.set_view_index(view, 2, 0)
