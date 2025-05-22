import sublime, threading, bisect
from ..settings import Settings
from ..utils import icon_path, color_for_key
from ..window.collection import DiffWindowCollection
from ..observable import Observable
from ..object import Object
TYPE_MISSING = "?"
TYPE_CHANGE = "."
TYPE_INSERTED = "+"
TYPE_REMOVED = "-"
TYPE_EQUAL = "="
TYPE_CONFLICT = "!"
TYPE_CONFLICT_RESOLVED = "!?"
COLORS = {TYPE_MISSING: (color_for_key("diff_block_deleted")), 
 TYPE_CHANGE: (color_for_key("diff_block_changed")), 
 TYPE_INSERTED: (color_for_key("diff_block_inserted")), 
 TYPE_REMOVED: (color_for_key("diff_block_deleted")), 
 TYPE_CONFLICT: (color_for_key("diff_block_conflict")), 
 TYPE_EQUAL: (color_for_key("diff_block_changed"))}
ICONS_GROUP_START_LEFT = {TYPE_MISSING: (icon_path("left1")), 
 TYPE_CHANGE: (icon_path("left2")), 
 TYPE_INSERTED: (icon_path("left3")), 
 TYPE_REMOVED: (icon_path("left4")), 
 TYPE_CONFLICT: (icon_path("conflict")), 
 TYPE_CONFLICT_RESOLVED: (icon_path("conflict")), 
 TYPE_EQUAL: (icon_path("equal1")), 
 "MERGED": {TYPE_MISSING: (icon_path("m_bline1")), 
            TYPE_CHANGE: (icon_path("m_bline2")), 
            TYPE_INSERTED: (icon_path("m_bline3")), 
            TYPE_REMOVED: (icon_path("m_bline4")), 
            TYPE_CONFLICT: (icon_path("m_conflict")), 
            TYPE_CONFLICT_RESOLVED: (icon_path("m_conflict")), 
            TYPE_EQUAL: (icon_path("m_equal1"))}}
ICONS_GROUP_START_RIGHT = {TYPE_MISSING: (icon_path("right1")), 
 TYPE_CHANGE: (icon_path("right2")), 
 TYPE_INSERTED: (icon_path("right3")), 
 TYPE_REMOVED: (icon_path("right4")), 
 TYPE_CONFLICT: (icon_path("conflict")), 
 TYPE_CONFLICT_RESOLVED: (icon_path("conflict")), 
 TYPE_EQUAL: (icon_path("equal2")), 
 "MERGED": {TYPE_MISSING: (icon_path("m_bline1")), 
            TYPE_CHANGE: (icon_path("m_bline2")), 
            TYPE_INSERTED: (icon_path("m_bline3")), 
            TYPE_REMOVED: (icon_path("m_bline4")), 
            TYPE_CONFLICT: (icon_path("m_conflict")), 
            TYPE_CONFLICT_RESOLVED: (icon_path("m_conflict")), 
            TYPE_EQUAL: (icon_path("m_equal1"))}}
ICONS_GROUP_MIDDLE = {TYPE_MISSING: (icon_path("vline1")), 
 TYPE_CHANGE: (icon_path("vline2")), 
 TYPE_INSERTED: (icon_path("vline3")), 
 TYPE_REMOVED: (icon_path("vline4")), 
 TYPE_CONFLICT: (icon_path("conflict")), 
 TYPE_CONFLICT_RESOLVED: (icon_path("conflict")), 
 "MERGED": {TYPE_MISSING: (icon_path("m_vline1")), 
            TYPE_CHANGE: (icon_path("m_vline2")), 
            TYPE_INSERTED: (icon_path("m_vline3")), 
            TYPE_REMOVED: (icon_path("m_vline4")), 
            TYPE_CONFLICT: (icon_path("m_conflict")), 
            TYPE_CONFLICT_RESOLVED: (icon_path("m_conflict"))}}
ICONS_GROUP_END = {TYPE_MISSING: (icon_path("eline1")), 
 TYPE_CHANGE: (icon_path("eline2")), 
 TYPE_INSERTED: (icon_path("eline3")), 
 TYPE_REMOVED: (icon_path("eline4")), 
 TYPE_CONFLICT: (icon_path("conflict")), 
 TYPE_CONFLICT_RESOLVED: (icon_path("conflict")), 
 "MERGED": {TYPE_MISSING: (icon_path("m_eline1")), 
            TYPE_CHANGE: (icon_path("m_eline2")), 
            TYPE_INSERTED: (icon_path("m_eline3")), 
            TYPE_REMOVED: (icon_path("m_eline4")), 
            TYPE_CONFLICT: (icon_path("m_conflict")), 
            TYPE_CONFLICT_RESOLVED: (icon_path("m_conflict"))}}
GROUP_ONE_LINE = {TYPE_MISSING: (icon_path("m_beline1")), 
 TYPE_CHANGE: (icon_path("m_beline2")), 
 TYPE_INSERTED: (icon_path("m_beline3")), 
 TYPE_REMOVED: (icon_path("m_beline4")), 
 TYPE_CONFLICT: (icon_path("m_conflict")), 
 TYPE_CONFLICT_RESOLVED: (icon_path("m_conflict"))}

class BaseRenderer:
    ARROWS = [
     ICONS_GROUP_START_RIGHT,
     ICONS_GROUP_START_LEFT,
     ICONS_GROUP_START_LEFT]

    @classmethod
    def get_icon(self, icon_set, line, is_single_line=False):
        change_type = line.get_change_type()
        if icon_set is None:
            return ""
        else:
            owning_lines = line.get_owning_lines()
            if change_type in [TYPE_CONFLICT, TYPE_CONFLICT_RESOLVED]:
                return icon_set["MERGED"][change_type]
            else:
                if owning_lines:
                    window = owning_lines.get_view().get_window()
                    if window.is_3way():
                        if line.get_view() is window.get_layout().get_merged().get_view():
                            if Settings.get("diff_block_renderer") == "gutter":
                                if is_single_line:
                                    return GROUP_ONE_LINE[line.get_type()]
                                return icon_set["MERGED"][line.get_type()]
                            return ""
                return icon_set[line.get_type()]
            return

    @classmethod
    def get_color(self, line):
        change_type = line.get_change_type()
        if change_type in [TYPE_CONFLICT, TYPE_CONFLICT_RESOLVED]:
            return COLORS[change_type]
        else:
            return COLORS[line.get_type()]

    @classmethod
    def _draw_line(self, view, line, icon_set, is_single_line=False, add_swap_handler=True):
        pointer = line.get_pointer()
        name = line.get_name() + "-gutter"
        name_missing = line.get_name() + "-missing"
        view.add_regions(name, [
         pointer], self.get_color(line), self.get_icon(icon_set, line, is_single_line), sublime.HIDDEN)
        if add_swap_handler:
            if icon_set in self.ARROWS and view.window():

                def refresh_icon(sender):
                    sublime.set_timeout((lambda : self._draw_line(view, line, self.ARROWS[view.window().get_view_index(view)[0]], is_single_line, False)), 100)

                window = DiffWindowCollection.find(view.window())
                layout = window.get_layout()
                layout.on("swap", refresh_icon)
                line.on("destroy", (lambda sender: layout.un("swap", refresh_icon)))
        if line.get_type() == line.TYPE_MISSING:
            view.add_regions(name_missing, [
             pointer], color_for_key("diff_block_missing"), "", sublime.DRAW_EMPTY)
        else:
            view.erase_regions(name_missing)
        line.un("destroy", self._on_line_destroy)
        line.on("destroy", self._on_line_destroy)

    @classmethod
    def _on_group_destroy(self, group):
        view = group.get_view()
        name = group.get_name()
        view.erase_regions(name + "-selected")
        view.erase_regions(name)

    @classmethod
    def _on_line_destroy(self, line):
        self.clear_line(line)

    @classmethod
    def clear_line(self, line):
        view = line.get_view()
        name = line.get_name()
        view.erase_regions(name + "-gutter")
        view.erase_regions(name + "-missing")


class GutterRenderer(BaseRenderer):

    @classmethod
    def render_line(self, view, line, i, count, icon_set=None):
        icon_set_given = icon_set is not None
        if icon_set is None:
            window = line.get_owning_lines().get_window()
            if view == window.get_layout().get_left().get_view():
                icon_set = ICONS_GROUP_START_RIGHT
            else:
                icon_set = ICONS_GROUP_START_LEFT
        if i == 0:
            self._draw_line(view, line, icon_set, count == 0)
        elif i < count:
            self._draw_line(view, line, ICONS_GROUP_MIDDLE, count == 0)
        elif i == count:
            self._draw_line(view, line, ICONS_GROUP_END, count == 0)
        return

    @classmethod
    def render_group_normal(self, view, group):
        view.erase_regions(group.get_name() + "-selected")

    @classmethod
    def render_minimap(self, view, group):
        lines = group.get_lines()
        if not lines:
            return
        else:
            current_color = None
            region = [None, None]
            drawn = []
            _get_color = self.get_color
            _drawn_append = drawn.append
            _view_add_regions = view.add_regions
            for line in lines:
                line_region = line.get_region()
                if region[0] is None:
                    region[0] = line_region.begin()
                    region[1] = line_region.end()
                    current_color = _get_color(line)
                else:
                    color = _get_color(line)
                    if color == current_color:
                        region[1] = line_region.end()
                    else:
                        to_draw = (group.get_name() + "-%d" % len(drawn),
                         [
                          sublime.Region(region[0], region[1])],
                         current_color,
                         "",
                         sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL)
                        _drawn_append(to_draw)
                        _view_add_regions(*to_draw)
                        region = [
                         region[1], line_region.end()]
                        current_color = color

            to_draw = (
             group.get_name() + "-%d" % len(drawn),
             [
              sublime.Region(region[0], region[1])],
             current_color,
             "",
             sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL)
            _drawn_append(to_draw)
            _view_add_regions(*to_draw)
            group.on("destroy", (lambda *args: [view.erase_regions(item[0]) for item in drawn]))
            return

    @classmethod
    def render_group_selected(self, view, group):
        lines = group.get_lines()
        color = color_for_key("diff_block_selected")
        if lines:
            view.add_regions(group.get_name() + "-selected", [
             sublime.Region(lines[0].get_region().begin(), lines[-1].get_region().end())], self.get_color(group.get_lines()[0]) if color == "auto" else color, "", sublime.DRAW_OUTLINED)


class OutlineRenderer(BaseRenderer):

    @classmethod
    def render_line(self, view, line, i, count, icon_set=None):
        window = line.get_owning_lines().get_window()
        if view == window.get_layout().get_left().get_view():
            icon_set = ICONS_GROUP_START_RIGHT
        else:
            icon_set = ICONS_GROUP_START_LEFT
        if i == 0:
            self._draw_line(view, line, icon_set, count == 0)
        elif line.get_type() == line.TYPE_MISSING:
            self._draw_line(view, line, None, count == 0)
        return

    @classmethod
    def render_minimap(self, view, group):
        group.on("destroy", self._on_group_destroy)
        self.render_group_normal(view, group)

    @classmethod
    def render_group_normal(self, view, group):
        lines = group.get_lines()
        if lines:
            view.add_regions(group.get_name(), [
             sublime.Region(lines[0].get_region().begin(), lines[-1].get_region().end())], self.get_color(lines[0]), "", sublime.DRAW_OUTLINED | sublime.DRAW_EMPTY)

    @classmethod
    def render_group_selected(self, view, group):
        lines = group.get_lines()
        color = color_for_key("diff_block_selected")
        if lines:
            flags = sublime.DRAW_OUTLINED
            if lines[0].get_type() == lines[0].TYPE_INSERTED:
                flags |= sublime.DRAW_EMPTY
            view.add_regions(group.get_name(), [
             sublime.Region(lines[0].get_region().begin(), lines[-1].get_region().end())], self.get_color(group.get_lines()[0]) if color == "auto" else color, "", flags)


class RendererLineObj:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, view=None, line=None, i=None, count=None, icon_set=None):
        if Object.DEBUG:
            Object.add(self)
        self.view = view
        self.line = line
        self.i = i
        self.count = count
        self.icon_set = icon_set

    def __int__(self):
        return self.line.get_pointer().begin()

    def __lt__(self, other_line_obj):
        return self.__int__() < int(other_line_obj)

    def __le__(self, other_line_obj):
        return self.__int__() <= int(other_line_obj)

    def __gt__(self, other_line_obj):
        return self.__int__() > int(other_line_obj)

    def __ge__(self, other_line_obj):
        return self.__int__() >= int(other_line_obj)

    def __eq__(self, other_line_obj):
        return self.line == other_line_obj.line

    def __ne__(self, other_line_obj):
        return self.line != other_line_obj.line

    def to_args(self):
        return (
         self.view, self.line, self.i, self.count, self.icon_set)

    def destroy(self):
        Object.free(self)


class SortedLinesCollection:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self):
        if Object.DEBUG:
            Object.add(self)
        self._lines = []

    def destroy(self):
        del self._lines

    def contains(self, line_obj):
        i = bisect.bisect_left(self._lines, line_obj)
        j = bisect.bisect_right(self._lines, line_obj)
        return line_obj in self._lines[i:j]

    def add(self, line_obj):
        self.remove(line_obj)
        if line_obj.line.is_destroyed():
            return
        line_obj.line.on("destroy", self._on_line_destroy)
        if not self._lines:
            self._lines.append(line_obj)
        elif line_obj > self._lines[-1]:
            self._lines.append(line_obj)
        elif line_obj < self._lines[0]:
            self._lines.insert(0, line_obj)
        else:
            bisect.insort_right(self._lines, line_obj)

    def append(self, line_obj):
        if line_obj.line.is_destroyed():
            return
        line_obj.line.on("destroy", self._on_line_destroy)
        self._lines.append(line_obj)

    def _on_line_destroy(self, line):
        self.remove(RendererLineObj(line=line))

    def remove(self, line_obj):
        if line_obj.line.is_destroyed():
            try:
                line_obj.line.un("destroy", self._on_line_destroy)
                self._lines.remove(line_obj)
            except:
                pass

            return
        lines = self._lines
        lo = 0
        hi = len(lines)
        needle = int(line_obj)
        while lo < hi:
            mid = (lo + hi) // 2
            midval = lines[mid]
            pointer = int(midval)
            if pointer < needle:
                lo = mid + 1
            elif pointer > needle:
                hi = mid
            else:
                self._lines.pop(mid)
                midval.line.un("destroy", self._on_line_destroy)
                return

    def lines_outside_region(self, region):
        begin = region.begin()
        end = region.end()
        for line_obj in self._lines[:]:
            if line_obj.line.is_destroyed():
                self._lines.remove(line_obj)
            else:
                point = int(line_obj)
                if point < region.begin() or point > region.end():
                    yield line_obj
                    continue

    def lines_in_region(self, region):
        lines = self._lines
        lo = 0
        hi = len(lines)
        begin = region.begin()
        end = region.end()
        while lo < hi:
            mid = (lo + hi) // 2
            midval = lines[mid]
            if midval.line.is_destroyed():
                lo += 1
                continue
            pointer = int(midval)
            if pointer < begin:
                lo = mid + 1
            elif pointer > end:
                hi = mid
            else:
                yield midval
                for i in reversed(range(lo, mid)):
                    try:
                        midval = lines[i]
                        if midval.line.is_destroyed():
                            continue
                        if int(midval) >= begin:
                            yield midval
                        else:
                            break
                    except:
                        pass

                for i in range(mid, hi):
                    try:
                        midval = lines[i]
                        if midval.line.is_destroyed():
                            continue
                        if int(midval) <= end:
                            yield midval
                        else:
                            break
                    except:
                        pass

                return


class Renderer(Observable):
    EVENTS = [
     "render_line"]
    RENDERERS = {"gutter": GutterRenderer, 
     "outline": OutlineRenderer}

    def __init__(self):
        Observable.__init__(self)
        renderer = Settings.get("diff_block_renderer")
        try:
            self._renderer = self.RENDERERS[renderer]
        except:
            self._renderer = self.RENDERERS["gutter"]

        self._positions = {}
        self._viewports = {}
        self._lines_to_render = {}
        self._lines_rendered = {}
        self._destroyed = False

    def destroy(self):
        if self._destroyed:
            return
        else:
            self._destroyed = True
            self.un()
            for key in self._lines_to_render:
                self._lines_to_render[key].destroy()
                self._lines_to_render[key] = None

            for key in self._lines_rendered:
                self._lines_rendered[key].destroy()
                self._lines_to_render[key] = None

            Object.free(self)
            return

    def _enlarge_viewport(self, viewport, view, is_forward):
        factor = Settings.get("beyond_viewport_rendering")
        x0, y0 = view.text_to_layout(viewport.begin())
        x1, y1 = view.text_to_layout(viewport.end())
        _, viewport_height = view.viewport_extent()
        y1 += viewport_height * factor
        y0 -= viewport_height * factor
        return sublime.Region(view.layout_to_text((x0, y0)), view.layout_to_text((x1, y1)))

    def _render_lines_in_viewport(self, diff_view, viewport):
        view_id = diff_view.get_view().id()
        position = diff_view.get_view().viewport_position()[1]
        if view_id not in self._positions:
            return
        viewport = self._enlarge_viewport(viewport, diff_view.get_view(), position > self._positions[view_id])
        self._viewports[view_id] = viewport
        self._positions[view_id] = position
        rendered = []
        _renderer_render_line = self._renderer.render_line
        _lines_to_render_remove = self._lines_to_render[view_id].remove
        _rendered_append = rendered.append
        _fire = self.fire
        _lines_in_region = self._lines_to_render[view_id].lines_in_region(viewport)
        for line_obj in _lines_in_region:
            _renderer_render_line(*line_obj.to_args())
            _lines_to_render_remove(line_obj)
            _rendered_append(line_obj)
            _fire("render_line", line_obj.line)

        _renderer_clear_line = self._renderer.clear_line
        _lines_rendered_remove = self._lines_rendered[view_id].remove
        _lines_to_render_add = self._lines_to_render[view_id].add
        _lines_rendered_add = self._lines_rendered[view_id].add
        _lines_outside_region = self._lines_rendered[view_id].lines_outside_region(viewport)
        for line_obj in _lines_outside_region:
            _renderer_clear_line(line_obj.line)
            _lines_rendered_remove(line_obj)
            _lines_to_render_add(line_obj)

        for line_obj in rendered:
            _lines_rendered_add(line_obj)

        del rendered

    def _force_render_lines_in_viewport(self, diff_view, viewport):

        def inner():
            try:
                self._render_lines_in_viewport(diff_view, viewport)
            except AttributeError:
                pass

        sublime.set_timeout(inner, 50)
        sublime.set_timeout(inner, 100)
        sublime.set_timeout(inner, 150)

    def render_viewport(self, diff_view):
        self._render_lines_in_viewport(diff_view, diff_view.get_view().visible_region())

    def render_line(self, view, line, i, count, icon_set=None, append=False):
        try:
            if line.is_destroyed():
                return
            view_id = view.id()
            viewport = view.visible_region()
            if view_id not in self._viewports:
                diff_view = line.get_owning_lines().get_view()
                self._viewports.update({view_id: viewport})
                self._lines_to_render.update({view_id: (SortedLinesCollection())})
                self._lines_rendered.update({view_id: (SortedLinesCollection())})
                self._positions.update({view_id: (view.viewport_position()[1])})
                diff_view.on("scroll", self._render_lines_in_viewport)
                diff_view.on("resize", self._force_render_lines_in_viewport)
                diff_view.on("scroll_stop", self._force_render_lines_in_viewport)
            pointer = int(line)
            line_obj = RendererLineObj(view, line, i, count, icon_set)
            if pointer >= viewport.begin() and pointer <= viewport.end():
                self._renderer.render_line(*line_obj.to_args())
                if append:
                    self._lines_rendered[view_id].append(line_obj)
                else:
                    self._lines_rendered[view_id].add(line_obj)
                self.fire("render_line", line)
            elif append:
                self._lines_to_render[view_id].append(line_obj)
            else:
                self._lines_to_render[view_id].add(line_obj)
        except Exception as e:
            import traceback
            print("Sublimerge: [FATAL renderer exception]")
            print(traceback.format_exc())

    def render_minimap(self, view, group):
        self._renderer.render_minimap(view, group)

    @classmethod
    def render_selected(self, view, group):
        renderer = Settings.get("diff_block_renderer")
        self.RENDERERS[renderer].render_group_selected(view, group)

    @classmethod
    def render_unselected(self, view, group):
        renderer = Settings.get("diff_block_renderer")
        self.RENDERERS[renderer].render_group_normal(view, group)
