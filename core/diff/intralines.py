import sublime, re, threading
from difflib import SequenceMatcher
from ..settings import Settings
from ..utils import prepare_to_compare, prepare_to_compare_white, prepare_to_compare_regexp, color_for_key, subtract_ranges
from ..observable import Observable
from ..object import Object

class DiffIntralines(Observable):
    EVENTS = [
     "destroy"]
    RE_WS_BEGIN = re.compile("(^[ \t\x0c\x0b]*)")
    RE_WS_MIDDLE = re.compile("([^ \t\x0c\x0b\r\n])([ \t\x0c\x0b]+)([^ \t\x0c\x0b\r\n])")
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, line_a, line_b):
        if Object.DEBUG:
            Object.add(self)
        Observable.__init__(self)
        self._line_a = line_a
        self._line_b = line_b
        self._regions = {}
        self._destroyed = False
        self._name = "intralines-%d-%d" % (line_a.get_lineno(), line_b.get_lineno())
        self._names = {}
        self.refresh()

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        self.fire("destroy")
        self.un()
        for view_id in self._names:
            for name in self._names[view_id]:
                self._line_a.get_view().erase_regions(name)
                self._line_b.get_view().erase_regions(name)

        Object.free(self)

    def is_destroyed(self):
        return self._destroyed

    def refresh(self):
        self._regions = {}
        a = self._line_a
        b = self._line_b
        begin1 = 0
        begin2 = 0
        middle1 = 0
        middle2 = 0
        text_begin_a = a.get_region().begin()
        text_begin_b = b.get_region().begin()
        text_a = prepare_to_compare(a.get_view_text(), ignore_white=False, ignore_regexp=False)
        text_b = prepare_to_compare(b.get_view_text(), ignore_white=False, ignore_regexp=False)
        diffs = [
         None, None]
        diffs_a = None
        diffs_b = None
        num = 0
        ws1 = ws2 = 0
        ignore_whitespace = Settings.get("ignore_whitespace")
        if "begin" in ignore_whitespace:
            begin1 = len(re.search(self.RE_WS_BEGIN, text_a).group(0))
            begin2 = len(re.search(self.RE_WS_BEGIN, text_b).group(0))
        if "middle" in ignore_whitespace:
            matches = re.finditer(self.RE_WS_MIDDLE, text_a)
            middle1 = sum([len(match.group(2)) - 1 for match in matches]) if matches else 0
            matches = re.finditer(self.RE_WS_MIDDLE, text_b)
            middle2 = sum([len(match.group(2)) - 1 for match in matches]) if matches else 0
        text_a = prepare_to_compare_white(text_a)
        text_b = prepare_to_compare_white(text_b)
        if text_a != "":
            if text_b != "":
                if text_a != text_b:
                    changes_threshold = Settings.get("intraline_changes_threshold")
                    s = SequenceMatcher(None, text_a, text_b)
                    opcodes = s.get_opcodes()
                    ratio = s.ratio() * 100
                    ratio_passes = ratio > changes_threshold
                    crlf_differs = text_a[-2:] != text_b[-2:]
                    if ratio_passes:
                        combine_threshold = Settings.get("intraline_combine_threshold")
                        for tag, i1, i2, j1, j2 in opcodes:
                            if tag != "equal":
                                i1 += begin1 + ws1 + (middle1 if i1 > 0 else 0)
                                i2 += begin1 + ws1 + (middle1 if i1 > 0 else 0)
                                j1 += begin2 + ws2 + (middle2 if j1 > 0 else 0)
                                j2 += begin2 + ws2 + (middle2 if j1 > 0 else 0)
                                if diffs_a is None:
                                    diffs_a = diffs[0] = [
                                     [
                                      i1, i2]]
                                    diffs_b = diffs[1] = [[j1, j2]]
                                    _append_a = diffs_a.append
                                    _append_b = diffs_b.append
                                else:
                                    num = len(diffs_a) - 1
                                    if i1 - diffs[0][num][1] <= combine_threshold:
                                        diffs_a[num][1] = i2
                                        diffs_b[num][1] = j2
                                    else:
                                        _append_a([i1, i2])
                                        _append_b([j1, j2])
                                        continue

                        Region = sublime.Region
                        if diffs_a is not None:
                            try:
                                for i in range(len(diffs_a)):
                                    a1 = diffs_a[i][0]
                                    a2 = diffs_a[i][1]
                                    b1 = diffs_b[i][0]
                                    b2 = diffs_b[i][1]
                                    important_a, unimportant_a = self._ignore_by_regexp(a, a1, a2)
                                    important_b, unimportant_b = self._ignore_by_regexp(b, b1, b2)
                                    color_a = color_for_key("diff_block_intraline_changed")
                                    color_b = color_for_key("diff_block_intraline_changed")
                                    if a1 == a2:
                                        color_a = color_for_key("diff_block_intraline_deleted")
                                        color_b = color_for_key("diff_block_intraline_inserted")
                                    elif b1 == b2:
                                        color_a = color_for_key("diff_block_intraline_inserted")
                                        color_b = color_for_key("diff_block_intraline_deleted")
                                    for i1, i2 in important_a:
                                        region_a = Region(text_begin_a + i1, text_begin_a + i2)
                                        self._add_region(a, region_a, color_a, True)

                                    for i1, i2 in unimportant_a:
                                        region_a = Region(text_begin_a + i1, text_begin_a + i2)
                                        self._add_region(a, region_a, color_a, False)

                                    for i1, i2 in important_b:
                                        region_b = Region(text_begin_b + i1, text_begin_b + i2)
                                        self._add_region(b, region_b, color_b, True)

                                    for i1, i2 in unimportant_b:
                                        region_b = Region(text_begin_b + i1, text_begin_b + i2)
                                        self._add_region(b, region_b, color_b, False)

                            except Exception as e:
                                import traceback
                                print("Error handling intraline differences:")
                                print(traceback.format_exc())

        style = Settings.get("intraline_style")
        unimportant_style = Settings.get("intraline_unimportant_style")
        self._draw(a.get_view(), style, unimportant_style)
        self._draw(b.get_view(), style, unimportant_style)
        return

    def _find_regexp_matches(self, line, begin, end):
        text = line.get_view_text()
        for regexp in Settings.get_unimportant_regexp():
            matches = regexp.finditer(text)
            if not matches:
                continue
            for match in matches:
                for g in range(regexp.groups):
                    mb = match.start(g + 1)
                    me = match.end(g + 1)
                    if mb >= begin and mb <= end or me >= begin and me <= end:
                        yield (
                         mb, me)
                        continue

    def _ignore_by_regexp(self, line, begin, end):
        ranges = list(self._find_regexp_matches(line, begin, end))
        return (
         subtract_ranges((
          begin, end), ranges),
         ranges)

    def _add_region(self, diff_view, region, color, important=True):
        _id = diff_view.get_view().id()
        if _id not in self._regions:
            self._regions.update({_id: []})
        self._regions[_id].append((region, color, important))

    def _draw(self, view, style, unimportant_style):
        styles = {"outlined": (sublime.DRAW_NO_FILL), 
         "filled": 0, 
         "squiggly_underline": (sublime.DRAW_SQUIGGLY_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE), 
         "solid_underline": (sublime.DRAW_SOLID_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE), 
         "stippled_underline": (sublime.DRAW_STIPPLED_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)}
        try:
            style = styles[style]
        except:
            style = styles["filled"]

        try:
            unimportant_style = styles[unimportant_style]
        except:
            unimportant_style = styles["squiggly_underline"]

        view_id = view.id()
        if view_id not in self._names:
            self._names.update({view_id: []})
        if view_id in self._regions:
            for name in self._names[view_id]:
                view.erase_regions(name)

            for i, (region, color, important) in enumerate(self._regions[view_id]):
                name = self._name + "-%i" % i
                self._names[view_id].append(name)
                view.add_regions(name, [
                 region], color, "", sublime.DRAW_EMPTY | sublime.HIDE_ON_MINIMAP | (style if important else unimportant_style))

        else:
            for name in self._names[view_id]:
                view.erase_regions(name)

            self._names[view_id] = []
