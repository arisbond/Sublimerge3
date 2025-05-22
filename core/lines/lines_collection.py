import sublime, sublime_plugin, time, pickle, re
from ..observable import Observable
from ..renderers.hunk_renderer import HunkRenderer
from ..renderers.groups_renderers import Renderer
from ..settings import Settings
from ..utils import subtract_regions, sort
from ..debug import console
from ..object import Object
from ..task import Task
from .lines_group import LinesGroup
from .line import Line

class LinesCollection(Observable):
    EVENTS = [
     'line_removed_by_user', 'line_inserted_by_user', 'line_modified_by_user', 
     'done', 'render_line', 'rendered']
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, diff_view):
        if Object.DEBUG:
            Object.add(self)
        Observable.__init__(self)
        self._diff_view = diff_view
        self._view = diff_view.get_view()
        self._hunk_renderer = None
        self._lines = {}
        self._groups = []
        self._change_renderer = Renderer()
        self._change_renderer.on("render_line", (lambda sender, line: self.fire("render_line", line)))
        return

    def destroy(self):
        while self._groups:
            self._groups.pop().un("destroy", self._on_group_destroy)

        for lineno in self._lines:
            self._lines[lineno].destroy()

        self._change_renderer.destroy()
        Object.free(self)

    def __iter__(self):
        return self._lines.copy().__iter__()

    def get_window(self):
        return self._diff_view.get_window()

    def get_view(self):
        return self._diff_view

    def initialize(self):
        self._hunk_renderer = HunkRenderer(self._view.substr(sublime.Region(0, self._view.size())))

    def render_hunk(self, hunk):
        self._hunk_renderer.render(hunk)

    def dump(self):
        keys = sorted(self._lines.keys())
        for k in keys:
            print(k, self._lines[k])

    def reset(self):
        text = self.get_text()
        self._hunk_renderer = HunkRenderer(text)

    def prepare_to_flush(self):
        for line in self._lines.copy().values():
            self.destroy_and_remove(line)

    def flush(self):
        console.timer_begin("diff flush")
        result = self._hunk_renderer.result()
        self._view.run_command("sublimerge_view_replace", {"begin": 0, 
         "end": (self._view.size()), 
         "text": (result[0])})
        _view = self._view
        _render_line = self._change_renderer.render_line
        _render_minimap = self._change_renderer.render_minimap
        _lines = self._lines
        _groups_append = self._groups.append
        _on_group_destroy = self._on_group_destroy
        _lines_update = _lines.update
        group = None
        for hunk in result[1]:
            count = len(hunk) - 1
            i = 0
            group = LinesGroup(self)
            _groups_append(group)
            _group_add_line = group.add_line
            group.on("destroy", _on_group_destroy)
            for lineno, linetype, changetype in hunk:
                line = Line(self, lineno, changetype)
                line.set_type(linetype)
                _lines_update({lineno: line})
                _group_add_line(line)
                _render_line(_view, line, i, count, None, True)
                i += 1

        def render_minimap():
            if hasattr(self, "_groups"):
                for group in self._groups:
                    _render_minimap(_view, group)

        Task.spawn(render_minimap)
        console.timer_end()
        return

    def _update_lineno_since(self, lineno, by):
        new_lines = {}
        for key in self._lines:
            line = self._lines[key]
            if key < lineno:
                new_lines.update({key: line})
            else:
                new_lines.update({(key + by): line})
                line.set_lineno(key + by)
            self._lines[key] = None

        self._lines = new_lines
        return

    def update_lineno_since(self, lineno, by):
        self._update_lineno_since(lineno, by)

    def create_empty_line(self, lineno):
        line = Line(self, lineno)
        self._update_lineno_since(lineno, 1)
        self._lines.update({lineno: line})
        self._diff_view.set_silent("modified", True)
        self._view.run_command("sublimerge_view_insert", {"begin": (self._view.text_point(lineno, 0)), 
         "text": "\n"})
        self._diff_view.set_silent("modified", False)
        return line

    def remove_line(self, lineno):
        if lineno in self._lines:
            self._lines[lineno].destroy()
            del self._lines[lineno]
        point = self._view.text_point(lineno, 0)
        region = self._view.full_line(point)
        self._diff_view.set_silent("modified", True)
        self._view.run_command("sublimerge_view_replace", {"begin": (region.begin()), 
         "end": (region.end()), 
         "text": ""})
        self._diff_view.set_silent("modified", False)
        self._update_lineno_since(lineno, -1)

    def removed_line_by_user(self, lineno):
        if lineno in self._lines:
            self._lines[lineno].destroy()
            del self._lines[lineno]
        self._update_lineno_since(lineno, -1)

    def destroy_and_remove(self, line):
        lineno = line.get_lineno()
        line.destroy()
        if lineno in self._lines:
            del self._lines[lineno]

    def get_line(self, lineno):
        if lineno not in self._lines:
            line = Line(self, lineno)
            self._lines.update({lineno: line})
            return line
        else:
            return self._lines[lineno]

    def set_line_type(self, lineno, line_type):
        line = self.get_line(lineno)
        if line_type == Line.TYPE_EQUAL:
            line.destroy()
            if lineno in self._lines:
                del self._lines[lineno]
        else:
            line.set_type(line_type)
            self._lines.update({lineno: line})

    def get_groups(self):
        return self._groups

    def get_group(self, index):
        return self._groups[index]

    def render_changes(self, lines_range=None):
        console.timer_begin("render changes")
        keys = sorted(self._lines.keys())
        count = len(keys)
        n = 0
        for group in self._groups[:]:
            group.destroy()

        group = None
        _render_line = self._change_renderer.render_line
        _render_minimap = self._change_renderer.render_minimap
        _lines = self._lines
        _groups = self._groups
        _fire = self.fire
        _view = self._view
        _on_group_destroy = self._on_group_destroy
        for i in range(count):
            key_lineno = keys[i]
            next_lineno = keys[i + 1] if i + 1 < count else None
            line = _lines[key_lineno]
            next_line = _lines[next_lineno] if next_lineno is not None else None
            if line.get_type() == line.TYPE_EQUAL:
                self.destroy_and_remove(line)
                continue
            if n == 0:
                group = LinesGroup(self)
                _groups.append(group)
                group.on("destroy", _on_group_destroy)
                _group_add_line = group.add_line
            if next_line and next_line.get_type() == next_line.TYPE_EQUAL or next_lineno is not None and key_lineno + 1 < next_lineno or next_lineno is None:
                if lines_range is None or key_lineno in lines_range:
                    _render_line(_view, line, n, n)
                _group_add_line(line)
                n = 0
            elif lines_range is None or key_lineno in lines_range:
                _render_line(_view, line, n, n + 1)
            _group_add_line(line)
            n += 1

        for group in _groups:
            _render_minimap(_view, group)

        self._change_renderer.render_viewport(self._diff_view)
        console.timer_end()
        _fire("rendered")
        return

    def _on_group_destroy(self, group):
        try:
            self._groups.remove(group)
        except ValueError as e:
            pass

    def get_text(self, range_region=None):
        if range_region is None:
            range_region = sublime.Region(0, self._view.size())
        lines_regions = sort(self._lines_regions(), (lambda a, b: a[0].get_lineno() - b[0].get_lineno()))
        regions = subtract_regions(range_region, [region for line, region in lines_regions if line.is_missing() and range_region.contains(region)])
        text = "".join([self._view.substr(region) for region in regions])
        if len(lines_regions) > 0:
            if lines_regions[-1][0].is_missing():
                if lines_regions[-1][0].get_lineno() == self._view.rowcol(self._view.size())[0]:
                    if text[-1] in ('\r', '\n'):
                        text = text[:-1]
        return text

    def _lines_regions(self):
        return [(self._lines[lineno], self._lines[lineno].get_region()) for lineno in self._lines]

    def _atomic_lines_update(self, new_lines, modified_lines):
        render_range = [
         None, None]

        def update_render_range(lineno, render_range):
            if render_range[0] is None or lineno < render_range[0]:
                render_range[0] = lineno
            if render_range[1] is None or lineno > render_range[1]:
                render_range[1] = lineno
            return

        new_names = []
        current_names = []
        new_line_by_name = {}
        current_line_by_name = {}
        for lineno in modified_lines:
            update_render_range(lineno, render_range)

        for lineno in self._lines:
            line = self._lines[lineno]
            current_names.append(line.get_name())
            current_line_by_name.update({(line.get_name()): line})

        for lineno in new_lines:
            _type, _change_type, _lineno = new_lines[lineno]
            new_line_by_name.update({_lineno: (_type, _change_type, lineno)})
            new_names.append(_lineno)

        new_names = set(new_names)
        current_names = set(current_names)
        to_add = list(new_names - current_names)
        to_remove = list(current_names - new_names)
        to_update = list(new_names & current_names)
        to_add = sort(to_add, (lambda a, b: new_line_by_name[a][2] - new_line_by_name[b][2]))
        to_remove = sort(to_remove, (lambda a, b: current_line_by_name[a].get_lineno() - current_line_by_name[b].get_lineno()))
        to_update = sort(to_update, (lambda a, b: current_line_by_name[a].get_lineno() - current_line_by_name[b].get_lineno()))
        render_lineno = []
        for name in to_remove:
            lineno = current_line_by_name[name].get_lineno()
            current_line_by_name[name].destroy()
            del current_line_by_name[name]
            del self._lines[lineno]
            update_render_range(lineno, render_range)

        for name in to_update:
            line = current_line_by_name[name]
            _type, _change_type, lineno = new_line_by_name[name]
            if line.get_type() != _type or line.get_change_type() != _change_type:
                line.set_type(_type)
                line.set_change_type(_change_type)
                update_render_range(lineno, render_range)
            elif lineno in modified_lines:
                self.fire("render_line", line)
            line.set_lineno(lineno)

        new_lines = {}
        for line in self._lines.values():
            new_lines.update({(line.get_lineno()): line})

        self._lines = new_lines
        for name in to_add:
            _type, _change_type, lineno = new_line_by_name[name]
            line = Line(self, lineno)
            line.set_type(_type)
            line.set_change_type(_change_type)
            self._lines.update({lineno: line})
            update_render_range(lineno, render_range)

        if render_range[0] is not None and render_range[1] is not None:
            self.render_changes(range(render_range[0] - 1, render_range[1] + 2))
        else:
            self.fire("rendered")
        return

    def serialize(self):
        lines = {}
        for lineno in self._lines:
            line = self._lines[lineno]
            lines.update({lineno: (
                      line.get_type(), line.get_change_type(), line.get_name())})

        return lines

    def unserialize(self, serialized, modified_lines):
        self._diff_view.set_silent("modified", True)
        self._diff_view.set_silent("selection_modified", True)
        self._atomic_lines_update(serialized, modified_lines)
        self._diff_view.set_silent("modified", False)
        self._diff_view.set_silent("selection_modified", False)
        self._diff_view.fire("selection_modified")
