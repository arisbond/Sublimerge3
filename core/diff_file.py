import os, re, sublime, traceback, shutil, tempfile
from .utils import fopen, create_tmp_working_copy, normalize_crlf, create_tmpfile, sanitize_title
from .object import Object

class _BaseFile:
    _view = None
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, read_only=False, title=None):
        if Object.DEBUG:
            Object.add(self)
        self._read_only = read_only
        self._title = title
        self._path = ""

    def get_title(self):
        return

    def get_path(self):
        return self._path

    def is_read_only(self):
        return self._read_only

    def is_temporary(self):
        return False

    def set_text(self, text):
        pass

    def get_text(self):
        return ""

    def get_crlf(self):
        return "\n"

    def get_view(self):
        return

    def destroy(self):
        pass


class LocalFile(_BaseFile):
    RE_CRLF = re.compile("\r\n")
    RE_CR = re.compile("\r[^\n]")
    RE_LF = re.compile("[^\r]\n")
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, path, temporary=False, read_only=False, title=None):
        if Object.DEBUG:
            Object.add(self)
        _BaseFile.__init__(self, read_only=read_only, title=title)
        self._temporary = temporary
        self._line_endings = None
        self._path = path
        self._working_path = create_tmp_working_copy(path)
        return

    def get_title(self):
        return self._title or os.path.basename(self._path or "")

    def get_path(self):
        return self._working_path

    def get_original_path(self):
        return self._path

    def is_temporary(self):
        return self._temporary

    def get_text(self):
        if not self._working_path:
            return ""
        f = fopen(self._working_path, "rb")
        if f:
            text = f.read()
            f.close()
            return text.decode(encoding="utf-8", errors="ignore")
        return ""

    def get_crlf(self):
        if self._line_endings is None:
            text = self.get_text()
            crlf = len(self.RE_CRLF.findall(text))
            cr = len(self.RE_CR.findall(text))
            lf = len(self.RE_LF.findall(text))
            most = max(crlf, cr, lf)
            if most == crlf:
                self._line_endings = "\r\n"
            elif most == cr:
                self._line_endings = "\r"
            elif most == lf:
                self._line_endings = "\n"
        return self._line_endings

    def save(self, diff_view):
        backup = create_tmp_working_copy(self._path)
        shutil.copyfile(self._path, backup)
        try:
            f = fopen(self._path, "wb")
            if f:
                text = diff_view.get_text()
                text = normalize_crlf(text, diff_view.get_view().line_endings())
                encoding = diff_view.get_view().settings().get("default_encoding")
                try:
                    text = text.encode(encoding)
                    print("Sublimerge: Saved file %s (%s)" % (self._path, encoding))
                except:
                    text = text.encode("UTF-8")
                    print("Sublimerge: Failed to encode %s with %s. Falling back to UTF-8" % (self._path, encoding))

                f.write(text)
                f.close()
        except Exception as e:
            shutil.copyfile(backup, self._path)
            sublime.error_message("Sublimerge\n\nFailed to save: %s\n\nPlease open console for more details." % self._path)
            print("Error: ", e)
            print(traceback.format_exc())
            print("Please send this error to: support@sublimerge.com")

    def destroy(self):
        if self._temporary:
            try:
                os.remove(self._working_path)
            except:
                pass

        Object.free(self)


class CurrentLocalFile(LocalFile):

    def __init__(self, view, read_only, temporary=False, title=None):
        self._view = view
        LocalFile.__init__(self, view.file_name(), temporary=temporary, read_only=read_only, title=title)

    def get_view(self):
        return self._view


class ViewFile(_BaseFile):
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

        def __init__(self, view, path="", title=""):
            if Object.DEBUG:
                Object.add(self)
            _BaseFile.__init__(self)
            self._view = view
            self._path = path or create_tmpfile(title or self.get_title())

    def destroy(self):
        try:
            os.remove(self._path)
        except:
            pass

        Object.free(self)

    def get_crlf(self):
        return {"Unix": "\n", 
         "Windows": "\r\n", 
         "CR": "\r"}[self._view.line_endings()]

    def get_title(self):
        return os.path.basename(self._view.file_name() or sanitize_title(self._view.name()))

    def get_text(self):
        return self._view.substr(sublime.Region(0, self._view.size()))

    def get_view(self):
        return self._view

    def save(self, diff_view):
        region = sublime.Region(0, self._view.size())
        self._view.run_command("sublimerge_view_replace", {"begin": (region.begin()), 
         "end": (region.end()), 
         "text": (diff_view.get_text())})


class ClipboardFile(_BaseFile):
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self):
        if Object.DEBUG:
            Object.add(self)
        _BaseFile.__init__(self)
        self._path = create_tmpfile("Clipboard")

    def destroy(self):
        try:
            os.remove(self._path)
        except:
            pass

        Object.free(self)

    def get_text(self):
        return sublime.get_clipboard()

    def save(self, diff_view):
        sublime.set_clipboard(diff_view.get_text())


class SnapshotFile(_BaseFile):

    def __init__(self, view, snapshot):
        self._snapshot = snapshot
        self._view = view
        self._path = create_tmpfile(snapshot["hash"])
        self._read_only = True

    def destroy(self):
        Object.free(self)

    def get_view(self):
        return self._view

    def get_title(self):
        return self._snapshot["name"]

    def get_text(self):
        return self._snapshot["src"]

    def save(self):
        pass


class ViewRegionFile(_BaseFile):
    _NUM = 0
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self, view, region):
        if Object.DEBUG:
            Object.add(self)
        self._view = view
        self._region = view.line(region)
        self._name = "sm-view-region-%d" % ViewRegionFile._NUM
        self._view.add_regions(self._name, [self._region])
        self._read_only = False
        self._path = create_tmpfile(self.get_title())
        ViewRegionFile._NUM += 1

    def destroy(self):
        Object.free(self)

    def get_view(self):
        return self._view

    def get_title(self):
        view = self._view
        region = self._region
        title = os.path.basename(view.file_name()) if view.file_name() else None
        title = title or sanitize_title(view.name())
        row_begin = view.rowcol(region.begin())[0] + 1
        row_end = view.rowcol(region.end())[0] + 1
        if row_begin == row_end:
            suffix = " [%d]" % row_begin
        else:
            suffix = " [%d:%d]" % (row_begin, row_end)
        return title + suffix

    def get_text(self):
        return self._view.substr(self._region)

    def save(self, diff_view):
        region = self._view.get_regions(self._name)[0]
        self._view.run_command("sublimerge_view_replace", {"begin": (region.begin()), 
         "end": (region.end()), 
         "text": (diff_view.get_text())})
        region = sublime.Region(region.begin(), region.begin() + len(diff_view.get_text()))
        self._view.sel().clear()
        self._view.sel().add(region)
        self._view.add_regions(self._name, [region])
