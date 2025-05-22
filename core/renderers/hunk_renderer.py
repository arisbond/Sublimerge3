from ..utils import splitlines
from ..object import Object

class HunkRenderer:
    TYPE_REMOVED = "-"
    TYPE_INSERTED = "+"
    TYPE_CHANGE = "."
    TYPE_MISSING = "?"
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, text):
        if Object.DEBUG:
            Object.add(self)
        self._offset = 0
        self._lines = splitlines(text)
        self._groups = []
        self._destroyed = False

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        Object.free(self)

    def _to_st_lineno(self, lineno):
        return self._offset + lineno - 1

    def result(self):
        return (
         "".join(self._lines), self._groups)

    def render(self, hunk):
        line_begin, line_end, missing_size, change_type = hunk
        missing_begin = target_line_begin = target_line_end = self._to_st_lineno(line_begin)
        group = []
        _lines_insert = self._lines.insert
        _to_st_lineno = self._to_st_lineno
        _append = group.append
        _TYPE_INSERTED = self.TYPE_INSERTED
        if line_end != 0:
            target_line_end = _to_st_lineno(line_end)
            missing_begin = _to_st_lineno(line_end + 1)
            for lineno in range(target_line_begin, target_line_end + 1):
                if lineno <= target_line_end + missing_size:
                    line = (
                     lineno, change_type, change_type)
                else:
                    line = (
                     lineno, _TYPE_INSERTED, change_type)
                _append(line)

        if missing_size > 0:
            for lineno in range(missing_begin, missing_begin + missing_size):
                _lines_insert(lineno, "\n")
                line = (lineno, self.TYPE_MISSING, change_type)
                _append(line)

        if missing_size > 0:
            self._offset += missing_size
        self._groups.append(group)
