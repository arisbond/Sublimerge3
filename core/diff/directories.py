import os, sublime
from filecmp import dircmp
from datetime import datetime
from ..utils import file_matches_list, cmp_to_key
from ..promise import Promise
from ..settings import Settings
from ..task import Task

class DiffInfo:

    def __init__(self, left, right, diffs):
        self.left = left
        self.right = right
        self.diffs = diffs

    def get_name(self):
        return self.left and self.left["name"] or self.right and self.right["name"]

    def __repr__(self):
        return "DiffInfo %s %s" % (id(self), self.left or self.right)


class DiffDirectories:

    def __init__(self, left, right):
        self._left = left
        self._right = right
        self._listing = None
        self._current_item = None
        return

    def update_max_len(self):
        last = self._listing["items"][-1]
        items = [
         last.left, last.right]
        for name in self._listing["max_len"]:
            for item in items:
                if item is not None:
                    length = len(str(item[name]))
                    if length > self._listing["max_len"][name]:
                        self._listing["max_len"][name] = length
                    continue

        return

    def is_file_ignored(self, filename):
        return file_matches_list(filename, Settings.get("dir_compare_ignore_files"))

    def listing(self):
        self._listing = {"items": [],  "left": (self._left), 
         "right": (self._right), 
         "max_len": {"name": 0, 
                     "type": 0, 
                     "size": 0, 
                     "modified": 0}}
        self._dc = dircmp(self._left, self._right, ignore=Settings.get("dir_compare_ignore_dirs"))
        dirs = []
        files = []
        for name in self._dc.left_only:
            if not os.path.isdir(os.path.join(self._left, name)):
                if self.is_file_ignored(name):
                    continue
                info = self._get_info(self._left, name)
                info["type"] = "+"
                if info["is_dir"]:
                    dirs.append(DiffInfo(info, None, 1))
            else:
                files.append(DiffInfo(info, None, 1))

        for name in self._dc.right_only:
            if not os.path.isdir(os.path.join(self._left, name)):
                if self.is_file_ignored(name):
                    continue
                info = self._get_info(self._right, name)
                info["type"] = "+"
                if info["is_dir"]:
                    dirs.append(DiffInfo(None, info, 1))
            else:
                files.append(DiffInfo(None, info, 1))

        for name in self._dc.common:
            if self.is_file_ignored(name):
                continue
            left_info = self._get_info(self._left, name)
            right_info = self._get_info(self._right, name)
            if left_info["is_dir"] or right_info["is_dir"]:
                dirs.append(DiffInfo(left_info, right_info, 0))
            else:
                files.append(DiffInfo(left_info, right_info, 0))
            if name in self._dc.diff_files:
                files[-1].diffs = 1
                files[-1].left["type"] = files[-1].right["type"] = "."
                continue

        dirs = sorted(dirs, key=cmp_to_key(self._sort_left))
        dirs = sorted(dirs, key=cmp_to_key(self._sort_right))
        files = sorted(files, key=cmp_to_key(self._sort_left))
        files = sorted(files, key=cmp_to_key(self._sort_right))
        for item in dirs:
            self._listing["items"].append(item)
            self.update_max_len()

        for item in files:
            self._listing["items"].append(item)
            self.update_max_len()

        return self._listing

    def _sort_left(self, a, b):
        if a is None or a.left is None or b is None or b.left is None:
            return 0
        else:
            return self._sort(a.left["name"], b.left["name"])

    def _sort_right(self, a, b):
        if a is None or a.right is None or b is None or b.right is None:
            return 0
        else:
            return self._sort(a.right["name"], b.right["name"])

    def _sort(self, a, b):
        if a is None or b is None:
            return 0
        else:
            a = a.upper()
            b = b.upper()
            return (a > b) - (a < b)

    def _get_info(self, path, name):
        fullpath = os.path.join(path, name)
        item = {"name": name, 
         "type": "=", 
         "size": None, 
         "modified": None, 
         "is_dir": None, 
         "path": fullpath}
        d = datetime.fromtimestamp(int(round(os.path.getmtime(fullpath))))
        item["modified"] = d.strftime(Settings.get("date_format"))
        if os.path.isdir(fullpath):
            item["size"] = self._get_dir_size(fullpath)
            item["is_dir"] = True
        else:
            item["size"] = os.path.getsize(fullpath)
            item["is_dir"] = False
        return item

    def _get_dir_size(self, start_path):
        total_size = 0
        for filename in os.listdir(start_path):
            if not self.is_file_ignored(filename):
                fp = os.path.join(start_path, filename)
                if not os.path.isdir(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except:
                        pass

                continue

        return total_size
