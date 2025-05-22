import sublime, sublime_plugin

class _TextCommand(sublime_plugin.TextCommand):
    _is_read_only = False

    def _begin(self):
        self._is_read_only = self.view.is_read_only()
        self.view.set_read_only(False)

    def _end(self):
        self.view.set_read_only(self._is_read_only)


class SublimergeViewRemoveLastLineCommand(_TextCommand):

    def run(self, edit):
        self._begin()
        self.view.erase(edit, self.view.full_line(sublime.Region(self.view.size(), self.view.size())))
        self._end()


class SublimergeViewEraseCommand(_TextCommand):

    def run(self, edit):
        self._begin()
        self.view.erase(edit, sublime.Region(0, self.view.size()))
        self._end()


class SublimergeViewAppendCommand(_TextCommand):

    def run(self, edit, text):
        self._begin()
        self.view.insert(edit, self.view.size(), text)
        self._end()


class SublimergeViewReplaceCommand(_TextCommand):

    def run(self, edit, begin, end, text, cv_id=None, seq_id=None):
        self._begin()
        self.view.replace(edit, sublime.Region(int(begin), int(end)), text)
        self._end()


class SublimergeViewInsertCommand(_TextCommand):

    def run(self, edit, begin, text, cv_id=None, seq_id=None):
        self._begin()
        self.view.insert(edit, int(begin), text)
        self._end()
