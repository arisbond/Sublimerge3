import sublime
from ..observable import Observable
from ..task_manager import TaskManager
from ..debug import console
from ..object import Object
from ..settings import Settings
from .splitter import Splitter
from .scroll_sync import ScrollSync
from .view.collection import DiffViewCollection

class Group(Observable):
    EVENTS = [
     "before_add_view", "add_view", "before_remove_view", "remove_view"]
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, number, diff_window):
        if Object.DEBUG:
            Object.add(self)
        Observable.__init__(self)
        self._views = []
        self._diff_window = diff_window
        self._number = number
        self._active_view = None
        self._destroyed = False
        return

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        for view in self._views:
            self.remove_view(view)

        self.un()
        Object.free(self)

    def get_number(self):
        return self._number

    def add_view(self, diff_view):
        if diff_view:
            if diff_view not in self._views:
                self._views.append(diff_view)
                self._diff_window.get_window().set_view_index(diff_view.get_view(), self._number, len(self._views) - 1)
                diff_view.set_group(self)
                self._active_view = diff_view
                diff_view.on("destroy", self._on_view_destroy, True)

    def remove_view(self, diff_view):
        if diff_view in self._views:
            diff_view.un("destroy", self._on_view_destroy)
            self._views.remove(diff_view)

    def get_views(self):
        return self._views or []

    def has_view(self, view):
        return view in self._views

    def get_active_view(self):
        return self._active_view

    def focus_view(self, view):
        w = self._diff_window.get_window()
        w.focus_group(self._number)
        w.focus_view(view.get_view())
        del w

    def _on_view_destroy(self, diff_view):
        self.set_silent("remove_view", True)
        self.set_silent("before_remove_view", True)
        self.remove_view(diff_view)
        self.set_silent("before_remove_view", False)
        self.set_silent("remove_view", False)


class DiffWindowLayout2(Observable):
    EVENTS = [
     "destroy", "swap"]
    GROUP_LEFT = 0
    GROUP_RIGHT = 1
    NUM_GROUPS = 2
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_window):
        if Object.DEBUG:
            Object.add(self)
        Observable.__init__(self)
        self._views = []
        self._groups = []
        self._destroyed = False
        self._diff_window = diff_window
        self._window = diff_window.get_window()
        self._original_layout = self._window.get_layout()
        self._create_layout()
        self._init_groups()
        self._scroll_sync = None
        self._focused_view = None
        self._swap_tasks = TaskManager(100)
        self._hide_sidebar()
        return

    def _hide_sidebar(self):
        try:
            if self._window.is_sidebar_visible():
                self._window.set_sidebar_visible(False)
        except:
            pass

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        self._scroll_sync.destroy()
        while self._groups:
            self._groups.pop().destroy()

        self._swap_tasks.destroy()
        self.fire("destroy")
        self.un()
        Object.free(self)

    def _create_layout(self):
        cells = [
         [
          0, 0, 1, 1], [1, 0, 2, 1]]
        swapped = Settings.get("start_swapped")
        self._window.set_layout({"cols": [
                  0.0, 0.5, 1.0], 
         "rows": [
                  0.0, 1.0], 
         "cells": (list(reversed(cells)) if swapped else cells)})

    def _init_groups(self):
        self._groups = [Group(i, self._diff_window) for i in range(self.NUM_GROUPS)]

    def get_active_views(self):
        return [group.get_active_view() for group in self._groups]

    def get_left(self):
        return self._groups[self.GROUP_LEFT].get_active_view()

    def get_right(self):
        return self._groups[self.GROUP_RIGHT].get_active_view()

    def get_diff_view_by_view(self, by_view):
        for view in self._views:
            if view.get_view().id() == by_view.id():
                return view

        return

    def get_focused_view(self):
        return self.get_diff_view_by_view(self._window.active_view())

    def unfreeze(self):
        pass

    def swap(self):
        left = self.get_left()
        right = self.get_right()
        self._groups[self.GROUP_LEFT].remove_view(left)
        self._groups[self.GROUP_RIGHT].remove_view(right)
        self._groups[self.GROUP_LEFT].add_view(right)
        self._groups[self.GROUP_RIGHT].add_view(left)
        sublime.set_timeout((lambda : self.fire("swap")), 10)

    def add_view(self, diff_view, group=None):
        if self._scroll_sync:
            self._scroll_sync.destroy()
        self._scroll_sync = ScrollSync(self._diff_window)
        self._views.append(diff_view)
        if group is None:
            group = self._window.active_group()
        self._groups[group].add_view(diff_view)
        diff_view.on("destroy", self._on_view_destroy)
        diff_view.on("focus", self._on_view_focus)
        return

    def sync_to(self, view):
        self._scroll_sync.sync_to(view)

    def sync_to_active(self):
        self.sync_to(self._window.active_view())

    def start_sync(self):
        self._scroll_sync.start()

    def stop_sync(self):
        self._scroll_sync.stop()

    def _on_view_focus(self, view):
        self._focused_view = view

    def _on_view_destroy(self, view):
        view.un("focus", self._on_view_focus)
        view.un("destroy", self._on_view_destroy)
        try:
            self._views.remove(view)
            if len(view.get_group().get_views()) == 0:
                self.destroy()
        except:
            pass


class DiffWindowLayoutDirectories(DiffWindowLayout2):

    def _create_layout(self):
        self._window.set_layout({"cols": [
                  0.0, 0.5, 1.0], 
         "rows": [
                  0.0, 1.0], 
         "cells": [
                   [
                    0, 0, 1, 1], [1, 0, 2, 1]]})


class DiffWindowLayoutTextAndDirectories(DiffWindowLayout2):
    GROUP_LEFT = 2
    GROUP_RIGHT = 3
    NUM_GROUPS = 4

    def _create_layout(self):
        self._window.set_layout({"rows": [
                  0.0, 0.25, 1.0], 
         "cells": [
                   [
                    0, 0, 1, 1], [1, 0, 2, 1], [0, 1, 1, 2], [1, 1, 2, 2]], 
         "cols": [
                  0.0, 0.5, 1.0]})

    def get_active_views(self):
        return [
         self._groups[self.GROUP_LEFT].get_active_view(),
         self._groups[self.GROUP_RIGHT].get_active_view()]

    def destroy(self):
        self._window.set_layout(self._original_layout)
        DiffWindowLayout2.destroy(self)


class DiffWindowLayoutSplitted(DiffWindowLayout2):
    GROUP_LEFT = 0
    GROUP_RIGHT = 1
    NUM_GROUPS = 2

    def __init__(self, *args):
        self._splitter = Splitter()
        DiffWindowLayout2.__init__(self, *args)

    def _create_layout(self):
        self._splitter.split()

    def get_active_views(self):
        return [
         self._groups[self.GROUP_LEFT].get_active_view(),
         self._groups[self.GROUP_RIGHT].get_active_view()]

    def destroy(self):
        self._splitter.restore()
        DiffWindowLayout2.destroy(self)


class DiffWindowLayout3(DiffWindowLayout2):
    GROUP_LEFT = 0
    GROUP_CENTER = 1
    GROUP_RIGHT = 2
    NUM_GROUPS = 3

    def _create_layout(self):
        swapped = Settings.get("start_swapped")
        if Settings.get("three_way_layout") == 1:
            merged_height = 1 - float(Settings.get("three_way_merged_height")) / 100
            cells = [[0, 0, 1, 1], [0, 1, 2, 2], [1, 0, 2, 1]]
            self._window.set_layout({"cells": (list(reversed(cells)) if swapped else cells), 
             "rows": [
                      0.0, merged_height, 1.0], 
             "cols": [
                      0.0, 0.5, 1.0]})
        else:
            cells = [[0, 0, 1, 1], [1, 0, 2, 1], [2, 0, 3, 1]]
            self._window.set_layout({"cells": (list(reversed(cells)) if swapped else cells), 
             "rows": [
                      0.0, 1.0], 
             "cols": [
                      0.0, 0.33, 0.67, 1.0]})

    def _on_view_remove_from_group(self, group, view):
        if len(group.get_views()) == 0:
            group.add_view(view)

    def get_active_views(self):
        return [self._groups[group].get_active_view() for group in [self.GROUP_LEFT, self.GROUP_CENTER, self.GROUP_RIGHT]]

    def get_merged(self):
        return self._groups[self.GROUP_CENTER].get_active_view()
