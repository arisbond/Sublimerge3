import sublime
from shutil import copyfile
from difflib import SequenceMatcher
from hashlib import sha1
import os, tempfile, re, random, textwrap, math, sys, subprocess
from datetime import datetime
from .settings import Settings
from .metadata import PROJECT_NAME
from ..vendor.chardet import detect

def color_for_key(setting):
    value = Settings.get(setting)
    if value.startswith("#"):
        return "sublimerge." + setting
    return value


def hashstr(text):
    return sha1(str(text).encode("utf-8")).hexdigest()


def error_message(text):
    sublime.error_message("Sublimerge\n\n" + str(text))


def info_message(text):
    sublime.message_dialog("Sublimerge\n\n" + str(text))


def truncate(text, length):
    text = text or ""
    if len(text) > length:
        text = textwrap.wrap(text, length - 3)[0].rstrip(',./;\'\\[]-=`~<>?:"|{}_+!@#$%^&*()') + "..."
    return text


def sanitize_title(text):
    if not text:
        return "untitled"
    return re.sub('[:\\\\/<>"|?*;]', " ", text).strip() or "untitled"


def splitlines(text, append=True):
    lines = re.split("(\r\n|\r|\n)", text)
    result = []
    for i in range(len(lines)):
        if i % 2 == 0:
            result.append(lines[i])
        elif append:
            result[-1] += lines[i]
            continue

    return result


def get_syntax_name(view):
    syntax = view.settings().get("syntax")
    if syntax:
        return os.path.splitext(syntax)[0]


def icon_path(icon_name):
    if int(sublime.version()) < 3014:
        extn = ""
        path = ".."
    else:
        path = "Packages"
        extn = ".png"
    return path + "/" + PROJECT_NAME + "/icons/" + icon_name + extn


def random_string(self, l=30):
    return "%030x" % random.randrange(16 ** l)


def _condense(l):
    l = sorted(l)
    temp = [
     l.pop(0)]
    for t in l:
        if t[0] <= temp[-1][1]:
            t2 = temp.pop()
            temp.append((t2[0], max(t[1], t2[1])))
        else:
            temp.append(t)

    return temp


def _subtract(l1, l2):
    l1 = _condense(l1)
    l2 = _condense(l2)
    i = 0
    for t in l2:
        while t[0] > l1[i][1]:
            i += 1
            if i >= len(l1):
                break

        if t[1] < l1[i][1] and t[0] > l1[i][0]:
            l1 = l1[:i] + [(l1[i][0], t[0]), (t[1], l1[i][1])] + l1[i + 1:]
        elif t[1] >= l1[i][1] and t[0] <= l1[i][0]:
            l1.pop(i)
        elif t[1] >= l1[i][1]:
            l1[i] = (l1[i][0], t[0])
        elif t[0] <= l1[i][0]:
            l1[i] = (t[1], l1[i][1])
            continue

    return l1


def subtract_regions(source, regions):
    if len(regions) == 0:
        return [source]
    return [sublime.Region(a, b) for a, b in _subtract([[source.begin(), source.end()]], [[region.begin(), region.end()] for region in regions])]


def subtract_ranges(source, regions):
    if len(regions) == 0:
        return [source]
    return [(a, b) for a, b in _subtract([[source[0], source[1]]], regions)]


def similarity_ratio(a, b):
    s = SequenceMatcher(None, a, b)
    return s.ratio() * 100


RE_WS_BEGIN = re.compile("(^[ \t\x0c\x0b]+)", re.MULTILINE)
RE_WS_END = re.compile("([ \t\x0c\x0b]+$)", re.MULTILINE)
RE_WS_MIDDLE = re.compile("([^ \t\x0c\x0b\r\n])([ \t\x0c\x0b]+)([^ \t\x0c\x0b\r\n])", re.MULTILINE)

def prepare_to_compare_white(text):
    ignore_white = Settings.get("ignore_whitespace")
    if "begin" in ignore_white:
        text = re.sub(RE_WS_BEGIN, "", text)
    if "end" in ignore_white:
        text = re.sub(RE_WS_END, "", text)
    if "middle" in ignore_white:
        text = re.sub(RE_WS_MIDDLE, "\\1 \\3", text)
    return text


def prepare_to_compare_regexp(text):
    return text


def prepare_to_compare(text, ignore_white=True, ignore_regexp=True):
    ignore_crlf = Settings.get("ignore_crlf")
    ignore_case = Settings.get("ignore_case")
    if ignore_crlf:
        text = normalize_crlf(text, "\n")
    if ignore_case:
        text = text.lower()
    if ignore_white:
        text = prepare_to_compare_white(text)
    if ignore_regexp:
        text = prepare_to_compare_regexp(text)
    return text


def normalize_crlf(text, crlf=None):
    if crlf == False:
        return text
    text = re.sub("\r\n", "\n", text)
    text = re.sub("\r", "\n", text)
    if crlf in ('Windows', '\r\n'):
        text = re.sub("\n", "\r\n", text)
    elif crlf in ('CR', '\r'):
        text = re.sub("\n", "\r", text)
    return text


def fopen(path, mode):
    try:
        return open(path, mode)
    except LookupError:
        return codecs.open(path, mode, "utf-8")


def is_binary(filename):
    if not filename:
        return False
    f = fopen(filename, "rb")
    try:
        CHUNKSIZE = 1024
        while 1:
            chunk = f.read(CHUNKSIZE)
            try:
                if "\x00" in chunk:
                    return True
            except:
                if b'\x00' in chunk:
                    return True

            if len(chunk) < CHUNKSIZE:
                break

    finally:
        f.close()

    return False


def cmp_to_key(mycmp):

    class K(object):

        def __init__(self, obj, *args):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0

    return K


def sort(what, sort_fn):
    return sorted(what, key=cmp_to_key(sort_fn))


def create_tmpfile_path(file_name):
    return os.path.join(tempfile.mkdtemp(), " " + os.path.basename(file_name))


def create_tmpfile(file_name):
    path = create_tmpfile_path(file_name)
    fopen(path, "w").close()
    return path


def create_suffixed_tmpfile_path(file_name):
    suffix = " " + os.path.basename(file_name)
    f = tempfile.NamedTemporaryFile(suffix=suffix)
    path = f.name
    f.close()
    return path


def create_tmp_working_copy(file_name):
    if not file_name:
        return
    else:
        path = create_tmpfile_path(file_name)
        copyfile(file_name, path)
        strategy = Settings.get("file_encoding_detection_strategy")
        if strategy:
            f = fopen(path, "rb")
            text = f.read()
            f.close()
            f = fopen(path, "wb")
            if strategy == "auto":
                try:
                    charset = detect(text)
                    text = text.decode(encoding=charset["encoding"]).encode("utf-8")
                    f.write(text)
                except Exception as e:
                    print("File encoding exception (auto detect): ", e)

            elif isinstance(strategy, list):
                for charset in strategy:
                    try:
                        text = text.decode(encoding=charset).encode("utf-8")
                        f.write(text)
                        break
                    except Exception as e:
                        print("File encoding exception (strategy): ", e)

            else:
                print("Unknown file_encoding_detection_strategy: ", strategy)
            f.close()
        return path


def is_view_comparable(view):
    blacklist_titles = [
     "Find Results", "Package Control Messages"]
    return not view.is_read_only() and view.name() not in blacklist_titles and not view.settings().get("sublimerge_off")


def get_first_different_dir(a, b):
    a1 = re.split("[/\\\\]", a)
    a2 = re.split("[/\\\\]", b)
    len2 = len(a2) - 1
    for i in range(len(a1)):
        if i > len2 or a1[i] != a2[i]:
            return a1[i]


def create_tmp_pair(path1, path2):
    base1 = " " + os.path.basename(path1)
    base2 = " " + os.path.basename(path2)
    if path1 != path2:
        tmp = tempfile.mkdtemp()
        dirs = (
         os.path.join(tmp, get_first_different_dir(path1, path2)), os.path.join(tmp, get_first_different_dir(path2, path1)))
        files = (os.path.join(dirs[0], base1), os.path.join(dirs[1], base2))
        for d in dirs:
            if not os.path.exists(d):
                os.mkdir(d)
                continue

        return files
    if base1 == base2:
        base1 = "%s (1)" % base1
        base2 = "%s (2)" % base2
    return (os.path.join(tempfile.mkdtemp(), base1), os.path.join(tempfile.mkdtemp(), base2))


def get_comparable_views(current_view=None, with_selection=False):

    def has_selection(view):
        return len(view.sel()) == 1 and view.sel()[0].size() > 0

    def sort_files(a, b):
        d = b["ratio"] - a["ratio"]
        if d == 0:
            return 0
        if d < 0:
            return -1
        if d > 0:
            return 1

    def prepare_list_item(name, dirname):
        if Settings.get("compact_files_list"):
            sp = os.path.split(name)
            if dirname is not None and dirname != "":
                dirname = " / " + dirname
            else:
                dirname = ""
            if len(sp[0]) > 56:
                p1 = sp[0][0:20]
                p2 = sp[0][-36:]
                return [
                 sp[1] + dirname, p1 + "..." + p2]
            else:
                return [
                 sp[1] + dirname, sp[0]]
        else:
            return name
        return

    views = []
    if current_view is None:
        current_view = sublime.active_window().active_view()
    if current_view is None:
        return
    all_views = sublime.active_window().views()
    ratios = []
    if current_view.is_read_only():
        return
    else:
        intelligent_files_sort = Settings.get("intelligent_files_sort") and current_view.file_name() is not None
        if intelligent_files_sort:
            original = os.path.basename(current_view.file_name() or current_view.name() or "<untitled>")
        for view in all_views:
            if view.id() != current_view.id() and not view.is_read_only() and is_view_comparable(view) and (view.file_name() is None or current_view.file_name() is None or not Settings.get("same_syntax_only") or view.settings().get("syntax") == current_view.settings().get("syntax")):
                add = False
                if with_selection and has_selection(current_view) and has_selection(view) or not with_selection:
                    f = view.file_name() or "path unknown/" + (view.name() or "<untitled>")
                    ratio = 0
                    if intelligent_files_sort:
                        ratio = SequenceMatcher(None, original, os.path.basename(f)).ratio()
                    ratios.append({"ratio": ratio, 
                     "file": f, 
                     "dirname": "", 
                     "view": view})
                continue

        ratiosLength = len(ratios)
        if ratiosLength > 0:
            ratios = sorted(ratios, key=cmp_to_key(sort_files))
            if Settings.get("compact_files_list"):
                for i in range(ratiosLength):
                    for j in range(ratiosLength):
                        if i != j:
                            sp1 = os.path.split(ratios[i]["file"])
                            sp2 = os.path.split(ratios[j]["file"])
                            if sp1[1] == sp2[1]:
                                ratios[i]["dirname"] = get_first_different_dir(sp1[0], sp2[0])
                                ratios[j]["dirname"] = get_first_different_dir(sp2[0], sp1[0])
                            continue

            for f in ratios:
                views.append((prepare_list_item(f["file"], f["dirname"]), f["view"]))

            return views
        else:
            return
        return


def get_file_type_from_view(view):
    if not view:
        return (None, None)
    else:
        syntax = view.settings().get("syntax") or "Plain text.tmLanguage"
        return (get_file_type_from_syntax_file(os.path.split(syntax)[1]), syntax)


def get_file_type_from_syntax_file(syntax_file):
    if syntax_file:
        syntax = re.match("(.+)\\.(tmLanguage|sublime-syntax)$", os.path.split(syntax_file)[1])
        if syntax is not None:
            return syntax.group(1)
    return


def template(tpl, data):
    if not isinstance(tpl, list):
        tpl = [
         tpl]
    ret = []
    regexp = re.compile("\\${([^}]+)}")
    for line in tpl:
        for match in regexp.finditer(line):
            variable = match.group(1)
            if variable not in data:
                raise Exception("Template `%s` refers to undefined variable `%s`" % (str(tpl), variable))
            line = line.replace(match.group(0), data[variable])

        ret.append(line)

    return ret


def decode(txt):
    if not hasattr(txt, "decode"):
        return txt
    try:
        return txt.decode("utf-8", "replace")
    except:
        return txt


def ordinal(n):
    if 10 <= n % 100 < 20:
        return str(n) + "th"
    return str(n) + {1: "st",  2: "nd",  3: "rd"}.get(n % 10, "th")


def relative_date(date):
    at = "at"
    today = datetime.now().replace(tzinfo=None)
    date = date.replace(tzinfo=None)
    diff = today - date.replace(hour=today.hour, minute=today.minute, second=today.second)
    days_ago = diff.days
    months_ago = today.month - date.month
    years_ago = today.year - date.year
    weeks_ago = int(math.ceil(days_ago / 7.0))
    hr = date.strftime("%H")
    if hr.startswith("0"):
        hr = hr[1:]
    wd = today.weekday()
    if date.minute == 0:
        time = hr
    else:
        time = "{0}:{1}".format(hr, date.strftime("%M"))
    md = "{day} {month}".format(day=ordinal(date.day), month=date.strftime("%B"))
    mdy = "{md} {year}".format(md=md, year=date.year)
    if days_ago == 0:
        datestr = "today {at} {time}"
    elif days_ago == 1:
        datestr = "yesterday {at} {time}"
    elif not (wd in (5, 6) and days_ago in (wd + 1, wd + 2)):
        pass
    if wd + 3 <= days_ago <= wd + 8:
        datestr = "{days_ago} days ago (last {weekday} {at} {time})"
    elif days_ago <= wd + 2:
        datestr = "{days_ago} days ago ({weekday} {at} {time})"
    elif years_ago == 1:
        datestr = "last year ({mdy} {at} {time})"
    elif years_ago > 1:
        datestr = "{years_ago} years ago ({mdy} {at} {time})"
    elif months_ago == 1:
        datestr = "last month ({md} {at} {time})"
    elif months_ago > 1:
        datestr = "{months_ago} months ago ({md} {at} {time})"
    else:
        datestr = "{days_ago} days ago ({md} {at} {time})"
    return datestr.format(time=time, weekday=date.strftime("%A"), day=ordinal(date.day), days=diff.days, days_ago=days_ago, month=date.strftime("%B"), years_ago=years_ago, months_ago=months_ago, weeks_ago=weeks_ago, year=date.year, at=at, md=md, mdy=mdy)


def shell_cmd(exe, cwd, skip_empty=True):
    encodings = [
     None,
     sys.getfilesystemencoding(),
     Settings.get("shell_fallback_encoding")]
    tried = []
    thrown = None
    for encoding in encodings:
        try:
            command = exe.encode(encoding) if encoding is not None else exe
            directory = cwd.encode(encoding) if encoding is not None else cwd
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, cwd=directory, shell=True)
            thrown = None
            break
        except (UnicodeEncodeError, LookupError) as thrown:
            tried.append(encoding)
            continue

    if thrown is not None:
        raise Exception("Failed to encode shell command (tried: %s). Consider setting `shell_fallback_encoding` to match your locale settings." % ", ".join(tried))
    output, errors = p.communicate()
    if p.returncode != 0 or errors:
        output_file = re.match('^.*>>?\\s*([\'"])?(.*?)([\'"])?$', exe)
        if output_file:
            if os.path.exists(output_file.group(2)):
                os.remove(output_file.group(2))
        sublime.error_message("Sublimerge\n\n%s\nExit code: %s" % (errors.decode("utf-8", "replace"), p.returncode))
        raise Exception("Sublimerge\n\n%s\n\nexited with status: %s\n\n\n%s" % (exe, p.returncode, errors.decode("utf-8", "replace")))
    for line in output.splitlines():
        line = line.decode("utf-8", "replace")
        if skip_empty:
            line = re.sub("(^\\s+$)|(\\s+$)", "", line)
            if line != "":
                yield line
        else:
            yield line

    return


def file_matches_list(the_file, the_list):
    the_file = os.path.basename(the_file)
    if the_file in the_list:
        return True
    ext = "*" + os.path.splitext(the_file)[1].lower()
    return ext in the_list


def common_path(p1, p2):
    p1 = p1.split(os.sep)
    p2 = p2.split(os.sep)
    common = []
    for i in range(0, min(len(p1), len(p2))):
        if p1[i] == p2[i]:
            common.append(p1[i])
        else:
            break

    return os.sep.join(common)
