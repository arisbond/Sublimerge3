import sublime, os
from ...utils import icon_path, color_for_key
from ...object import Object
TYPE_REMOVED = "-"
TYPE_CHANGE = "."
TYPE_INSERTED = "+"
SIDE_LEFT = "left"
SIDE_RIGHT = "right"
COLORS = {TYPE_CHANGE: (color_for_key("diff_block_changed")), 
 TYPE_INSERTED: (color_for_key("diff_block_inserted")), 
 TYPE_REMOVED: (color_for_key("diff_block_deleted"))}
ICONS = {SIDE_RIGHT: {TYPE_CHANGE: (icon_path("left1")), 
              TYPE_INSERTED: (icon_path("left2")), 
              TYPE_REMOVED: (icon_path("left3"))}, 
 SIDE_LEFT: {TYPE_CHANGE: (icon_path("right1")), 
             TYPE_INSERTED: (icon_path("right2")), 
             TYPE_REMOVED: (icon_path("right3"))}}

class Item:

    def __init__(self, name, data, diff_view, side, is_header):
        self._diff_view = diff_view
        self._is_header = is_header
        self._rendered = False
        self._region = None
        self._row = None
        self._on_swap_attached = False
        self._side = side
        self._update(data)
        self._selected = False
        self._region_name = "sm-file-%s" % name
        self._region_name_missing = "sm-file-miss-%s" % name
        self._region_name_minimap = "sm-file-minimap-%s" % name
        return

    def destroy(self):
        self.clear()
        view = self._diff_view.get_view()
        view.run_command("sublimerge_view_replace", {"begin": (self._region.begin()), 
         "end": (self._region.end()), 
         "text": ""})
        Object.free(self)

    def _update(self, data):
        self.modified = data["modified"] if data and "modified" in data else ""
        self.name = data["name"] if data and "name" in data else ""
        self.size = data["size"] if data and "size" in data else ""
        self.is_dir = data["is_dir"] if data and "is_dir" in data else None
        self.type = data["type"] if data and "type" in data else "-" if not self._is_header else None
        self.path = data["path"] if data and "path" in data else None
        return

    def set_row(self, row):
        self._row = row
        self._update_region()

    def get_row(self):
        return self._row

    def _update_region(self):
        view = self._diff_view.get_view()
        point = view.text_point(self._row, 0)
        self._region = view.full_line(point)

    def get_region(self):
        return self._region

    def set_type(self, type):
        self.type = type
        self.render_icon()

    def get_type(self):
        return self.type

    def is_missing(self):
        return self.type == TYPE_REMOVED

    def is_dir(self):
        return self.is_dir

    def get_sub(self):
        return self._sub

    def update(self, data):
        self._update(data)
        self._update_region()
        self.render_icon()

    def select(self):
        self._selected = True
        self._diff_view.get_view().add_regions("sm-selection", [
         self._region], color_for_key("diff_block_selected"), "", sublime.DRAW_NO_FILL | sublime.HIDE_ON_MINIMAP)

    def unselect(self):
        self._selected = False
        self._diff_view.get_view().erase_regions("sm-selection")

    def render_icon(self):
        view = self._diff_view.get_view()
        if self.type in [TYPE_REMOVED, TYPE_INSERTED, TYPE_CHANGE]:
            pointer = sublime.Region(self._region.begin(), self._region.begin())
            view.add_regions(self._region_name, [
             pointer], COLORS[self.type], ICONS[self._side][self.type], sublime.HIDDEN)
            view.add_regions(self._region_name_minimap, [
             self._region], COLORS[self.type], "", sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL)
            if self.type == TYPE_REMOVED:
                view.add_regions(self._region_name_missing, [
                 pointer], color_for_key("diff_block_missing"), "", sublime.DRAW_EMPTY)
            if not self._on_swap_attached:
                self._on_swap_attached = True
                self._diff_view.get_window().get_layout().on("swap", self._on_swap_handler)
        else:
            self.clear()

    def clear(self):
        if self._on_swap_attached:
            self._diff_view.get_window().get_layout().un("swap", self._on_swap_handler)
        view = self._diff_view.get_view()
        view.erase_regions(self._region_name)
        view.erase_regions(self._region_name_missing)
        view.erase_regions(self._region_name_minimap)

    def render(self, max_len):
        view = self._diff_view.get_view()
        row_size = round(view.viewport_extent()[0] / view.em_width())
        text = self._item_row(row_size, max_len) + "\n"
        if not self._rendered:
            self._row, _ = view.rowcol(view.size())
        else:
            self._update_region()
            view.run_command("sublimerge_view_replace", {"begin": (self._region.begin()), 
             "end": (self._region.end()), 
             "text": text})
            self._update_region()
            self.render_icon()
        self._rendered = True
        return text

    def _on_swap_handler(self, sender):
        self._side = SIDE_LEFT if self._side == SIDE_RIGHT else SIDE_RIGHT
        self.render_icon()

    def _item_row(self, row_size, max_len):
        order = [
         "size", "modified"]
        columns = {"size": (self.size if not self.is_dir else "-"),  "modified": (self.modified)}
        output = []
        for column in order:
            value = str(columns[column])
            pad = " " * (max_len[column] - len(value))
            output.append(value + pad)

        suffix = "  ".join(output)
        diff_len = int(row_size) - len(suffix)
        if diff_len < 18:
            row_size += 18 - diff_len
        if self._is_header:
            name = self.name
        else:
            name = self._name_dir(self.name) if self.is_dir else self._name_file(self.name)
        pad_len = int(row_size - len(name) - len(suffix) - 3)
        if pad_len >= 1:
            pad = " " * pad_len
        elif self.is_dir:
            sep = name[-1]
            name = name[0:pad_len - 5] + "..." + sep + " "
        else:
            name = name[0:pad_len - 4] + "... "
        return name + pad + suffix

    def _name_dir(self, name):
        if not name:
            return ""
        try:
            c = unichr(9656)
        except:
            c = chr(9656)

        return " %s %s%s" % (c, name, os.sep)

    def _name_file(self, name):
        if not name:
            return ""
        try:
            c = unichr(8801)
        except:
            c = chr(8801)

        return " %s %s" % (c, name)
