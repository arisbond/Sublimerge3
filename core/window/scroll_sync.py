import sublime, threading
from math import ceil
from time import sleep
from ..debug import console
from ..promise import Promise
from ..object import Object

class Scroller:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_view, proportionally_x=False, proportionally_y=True):
        if Object.DEBUG:
            Object.add(self)
        self.diff_view = diff_view
        self.view = diff_view.get_view()
        self.last_position = None
        self.proportionally_x = proportionally_x
        self.proportionally_y = proportionally_y
        self.visible_region = None
        self.reset()
        return

    def destroy(self):
        Object.free(self)

    def sync_to(self, scroller_active):
        if not scroller_active:
            return
        v = scroller_active.view
        pos = v.viewport_position()
        ve = v.viewport_extent()
        le = v.layout_extent()
        v = self.view
        self_ve = v.viewport_extent()
        self_le = v.layout_extent()
        if self.proportionally_x:
            percentage_x = min(1, pos[0] / (1 if le[0] <= ve[0] else le[0] - ve[0]))
            pos_x = max(0, min(ceil(percentage_x * (self_le[0] - self_ve[0])), self_le[0] - self_ve[0]))
        else:
            pos_x = max(0, min(pos[0], self_le[0] - self_ve[0]))
        if self.proportionally_y:
            percentage_y = min(1, pos[1] / (1 if le[1] <= ve[1] else le[1] - ve[1]))
            pos_y = max(0, min(ceil(percentage_y * (self_le[1] - self_ve[1])), self_le[1] - self_ve[1]))
        else:
            pos_y = max(0, min(pos[1], self_le[1] - self_ve[1]))
        self.target_pos = (
         pos_x,
         pos_y)
        v.set_viewport_position(self.target_pos, False)
        self.on_scroll()

    def on_scroll(self):
        visible_region = self.view.visible_region()
        if visible_region != self.visible_region:
            self.diff_view.on_scroll(visible_region)
            self.visible_region = visible_region

    def on_scroll_stop(self):
        visible_region = self.view.visible_region()
        self.diff_view.on_scroll_stop(visible_region)

    def is_stopped(self):
        pos = self.view.viewport_position()
        if pos == self.last_position:
            return True
        self.last_position = pos
        return False

    def is_synced(self):
        v = self.view
        p = v.viewport_position()
        ve = v.viewport_extent()
        le = v.layout_extent()
        pos = (
         max(0, min(p[0], le[0] - ve[0])), max(0, min(p[1], le[1] - ve[1])))
        return pos == self.target_pos

    def reset(self):
        v = self.view
        p = v.viewport_position()
        ve = v.viewport_extent()
        le = v.layout_extent()
        self.target_pos = (
         max(0, min(p[0], le[0] - ve[0])), max(0, min(p[1], le[1] - ve[1])))


class ScrollSync:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_window):
        if Object.DEBUG:
            Object.add(self)
        self.interval = 10
        self.scrollers = [Scroller(view) for view in diff_window.get_views()]
        self.scrollers_to_sync = []
        self.scroller_active = None
        self.enabled = False
        self.stored = None
        self.watch = None
        self.thread = None
        self.scrolled_promise = None
        return

    def destroy(self):
        self.enabled = False
        while self.scrollers:
            self.scrollers.pop().destroy()

        Object.free(self)

    def store(self):
        self.stored = [scroller.view.viewport_position() for scroller in self.scrollers]

    def sync_to(self, view):
        if not view:
            return
        self.stop()
        self.scrollers_to_sync = []
        for scroller in self.scrollers:
            if scroller.view.id() == view.id():
                self.watch = scroller
                scroller.on_scroll()
                break

        self.scrollers_to_sync = [s for s in self.scrollers if s is not self.watch]
        for s in self.scrollers_to_sync:
            s.sync_to(self.watch)

    def restore(self):

        def inner():
            if self.stored is not None:
                for i in range(0, len(self.scrollers)):
                    self.scrollers[i].view.set_viewport_position(self.stored[i], False)

                self.stored = None
            for scroller in self.scrollers:
                scroller.reset()

            return

        sublime.set_timeout(inner, 100)

    def start(self):
        self.watch = None
        self.enabled = True
        self.thread = threading.Thread(target=self.sync).start()
        return

    def stop(self):
        self.enabled = False
        self.scroller_active = None
        for s in self.scrollers:
            s.reset()

        return

    def on_scroll_stop(self):
        for s in self.scrollers:
            s.on_scroll_stop()

    def sync(self):
        try:
            if not self.enabled:
                return
        except:
            return

        if not self.scroller_active:
            for scroller in self.scrollers:
                if not self.watch and not scroller.is_synced():
                    if self.scrolled_promise:
                        self.scrolled_promise.reject()
                    self.scrolled_promise = Promise().then(self.on_scroll_stop)
                    self.scroller_active = scroller
                    self.scrollers_to_sync = [s for s in self.scrollers if s is not scroller]
                    scroller.on_scroll()
                    for s in self.scrollers_to_sync:
                        s.sync_to(self.scroller_active)

                    break

        elif self.scroller_active.is_stopped() or all(s.is_synced() for s in self.scrollers_to_sync) and not self.watch:
            self.scroller_active.reset()
            self.scroller_active.on_scroll()
            for s in self.scrollers_to_sync:
                s.sync_to(self.scroller_active)

            self.scrollers_to_sync = []
            self.scroller_active = None
            sublime.set_timeout(self.scrolled_promise.resolve, 100)
        if self.enabled:
            sublime.set_timeout(self.sync, self.interval)
        return
