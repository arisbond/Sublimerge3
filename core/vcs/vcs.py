import os, sublime, re, tempfile
from time import sleep
from ..settings import Settings
from ..debug import console
from ..task_manager import TaskManager
from ..promise import Promise
from ..task import Task
from ..utils import fopen

class VCS:
    GIT = "git"
    SVN = "svn"
    HG = "hg"
    ALL = [
     GIT, SVN, HG]
    PATH_RE = re.compile("[/\\\\]+")
    CACHE_FILE_NAME = "Sublimerge.vcs-cache"
    THREAD_SLEEP_VALUE = 1e-06
    _vcs_cache = {}
    _no_vcs_cache = {}
    _initializing = False
    _initialized = False
    _init_queue = []
    _task_manager = TaskManager(2000)
    _initialized_promise = Promise()
    _path_initialized_promise = None

    @staticmethod
    def initialize():
        if not Settings.get("vcs_support") or not Settings.get("vcs_cache_enabled"):
            VCS._initialized_promise.reject()
            return
        VCS._read_from_file()
        if not Settings.get("vcs_cache_validate_on_startup"):
            VCS._initialized_promise.resolve()
            return
        VCS.validate().then(VCS._initialized_promise.resolve)

    @staticmethod
    def validate():
        return Task.spawn(VCS._validate_cache).progress("Sublimerge: Validating VCS cache")

    @staticmethod
    def init_path(path):
        if not path:
            return
        else:
            if not VCS._initialized_promise.is_resolved() and not VCS._initialized_promise.is_resolved():
                console.log("Queue init_path() after initialize()")
                VCS._initialized_promise.then((lambda *result: VCS.init_path(path)))
                return
            is_git = VCS._vcs_cache_read(VCS.GIT, path)
            is_svn = VCS._vcs_cache_read(VCS.SVN, path)
            is_hg = VCS._vcs_cache_read(VCS.HG, path)
            if is_git is None or is_svn is None or is_hg is None:
                VCS._init_queue.append(path)
                if VCS._path_initialized_promise is None or VCS._path_initialized_promise.is_resolved():
                    VCS._path_initialized_promise = Promise()
                    Task.spawn(VCS._init_queued_paths_task).progress("Sublimerge: Initializing VCS cache").then(VCS._path_initialized_promise.resolve)
            else:
                console.log("Git:", is_git, ", SVN:", is_svn, ", Hg:", is_hg, ", (" + path + ")")
            return

    @staticmethod
    def root(vcs, view=None, file_name=None):
        if not vcs:
            return False
        else:
            if vcs is None:
                vcs = VCS.which()
            if vcs not in VCS.ALL:
                console.error("Unknown VCS type:", vcs)
                return False
            else:
                if view is None:
                    if file_name is None:
                        view = sublime.active_window().active_view()
                if view is not None:
                    file_name = view.file_name()
                if not file_name:
                    return False
                cached = VCS._vcs_cache_read(vcs, file_name)
                if cached is not None:
                    pass
                return cached
            return VCS._vcs_cache_write(vcs, VCS._read_up(vcs, file_name))

    @staticmethod
    def unroot(file_name, vcs=None):
        root = VCS.root(vcs, file_name=file_name)
        if root:
            if file_name.startswith(root):
                file_name = file_name[len(root):]
                if file_name.startswith("/") or file_name.startswith("\\"):
                    file_name = file_name[1:]
        return file_name

    @staticmethod
    def which(view=None, file_name=None):
        for vcs in Settings.get("vcs_discovery_order"):
            if VCS.root(vcs, view, file_name):
                return vcs

        return

    @staticmethod
    def purge():
        console.log("Purge VCS cache")
        VCS._vcs_cache = {}
        VCS._no_vcs_cache = {}
        VCS._save_to_file()

    @staticmethod
    def merge_cleanup(path):
        vcs = VCS.which(file_name=path)
        dir_name, file_name = os.path.split(path)
        file_name_no_ext, file_ext = os.path.splitext(file_name)
        regexps = None
        if vcs == VCS.GIT:
            orig = path + ".orig"
            try:
                if os.path.exists(orig):
                    os.remove(orig)
            except Exception as e:
                pass

            regexps = [
             re.compile("^" + re.escape(file_name_no_ext) + ".BACKUP.\\d+" + re.escape(file_ext) + "$"),
             re.compile("^" + re.escape(file_name_no_ext) + ".BASE.\\d+" + re.escape(file_ext) + "$"),
             re.compile("^" + re.escape(file_name_no_ext) + ".LOCAL.\\d+" + re.escape(file_ext) + "$"),
             re.compile("^" + re.escape(file_name_no_ext) + ".REMOTE.\\d+" + re.escape(file_ext) + "$")]
        elif vcs == VCS.SVN:
            regexps = [re.compile("^" + re.escape(file_name) + "\\.merge-left\\.r\\d+$"),
             re.compile("^" + re.escape(file_name) + "\\.merge-right\\.r\\d+$"),
             re.compile("^" + re.escape(file_name) + "\\.working$")]
        elif vcs == VCS.HG:
            pass
        if regexps:
            for file_in_dir in os.listdir(dir_name):
                for regexp in regexps:
                    if regexp.match(file_in_dir):
                        try:
                            path = os.path.join(dir_name, file_in_dir)
                            if os.path.exists(path):
                                os.remove(os.path.join(dir_name, file_in_dir))
                        except Exception as e:
                            pass

                        continue

        return

    @staticmethod
    def _init_queued_paths_task():
        while len(VCS._init_queue) > 0:
            path = VCS._init_queue.pop()
            console.log("Run queued _init_path:", path)
            sleep(VCS.THREAD_SLEEP_VALUE)
            VCS._init_path(path, VCS.ALL.copy())

        VCS._task_manager.remove(VCS._save_to_file)
        VCS._task_manager.add(VCS._save_to_file)
        return True

    @staticmethod
    def _init_path(path, vcss):
        orig_path = path

        def traverse(path, vcss):
            if len(vcss) > 0:
                sp = os.path.split(path)
                for vcs in vcss:
                    cached = VCS._vcs_cache_read(vcs, path)
                    if cached is None:
                        vcs_path = os.path.join(path, "." + vcs)
                        if os.path.exists(vcs_path):
                            console.log("Found", vcs, "path:", orig_path)
                            VCS._vcs_cache_write(vcs, path)
                            vcss.remove(vcs)
                    else:
                        console.log("Got cached", vcs, "for path", orig_path, ":", cached)
                        vcss.remove(vcs)

                if sp[0] != path and sp[0] != "":
                    traverse(sp[0], vcss)
                else:
                    for vcs in vcss:
                        console.log("No", vcs, "repo (caching False): ", orig_path)
                        VCS._no_vcs_cache_write(vcs, orig_path)

            return

        traverse(path, vcss)

    @staticmethod
    def _read_up(vcs, path):
        if not path:
            return False
        else:
            if VCS._is_sub_path(tempfile.gettempdir(), path):
                return False
            else:
                if os.path.exists(os.path.join(path, "." + vcs)):
                    return path
                sp = os.path.split(path)
                if sp[0] != path and sp[0] != "":
                    pass
                return VCS._read_up(vcs, sp[0])
            return False

    @staticmethod
    def _read_down(vcs, path):
        if not path:
            return False
        else:
            if VCS._is_sub_path(tempfile.gettempdir(), path):
                return False
            if not os.path.isdir(path):
                path = os.path.dirname(path)
            if os.path.exists(os.path.join(path, "." + vcs)):
                pass
            return path
        sleep(VCS.THREAD_SLEEP_VALUE)
        for name in os.listdir(path):
            if name[0] != ".":
                new_path = os.path.join(path, name)
                if os.path.isdir(new_path):
                    vcs_path = VCS._read_down(vcs, new_path)
                    if vcs_path:
                        return vcs_path
                continue

        return False

    @staticmethod
    def _is_sub_path(a, b):
        if not a or not b:
            return False
        a = re.split(VCS.PATH_RE, a)
        b = re.split(VCS.PATH_RE, b)
        len_a = len(a)
        len_b = len(b)
        if len_a > len_b:
            return False
        for i in reversed(range(len_a)):
            if a[i] != b[i]:
                return False

        return True

    @staticmethod
    def _path_contains(path, contained):
        return path == contained or os.path.dirname(contained) == path

    @staticmethod
    def _no_vcs_cache_write(vcs, file_path):
        if VCS._is_sub_path(tempfile.gettempdir(), file_path):
            return
        if vcs not in VCS._no_vcs_cache:
            VCS._no_vcs_cache.update({vcs: []})
        file_path = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
        if file_path not in VCS._no_vcs_cache[vcs]:
            VCS._no_vcs_cache[vcs].append(file_path)

    @staticmethod
    def _no_vcs_cache_read(vcs, file_name):
        if vcs not in VCS._no_vcs_cache:
            return False
        for vcs_path in VCS._no_vcs_cache[vcs]:
            if VCS._path_contains(vcs_path, file_name):
                return True

        return False

    @staticmethod
    def _vcs_cache_read(vcs, file_path):
        if VCS._no_vcs_cache_read(vcs, file_path):
            return False
        else:
            if vcs not in VCS._vcs_cache:
                return
            for vcs_path in VCS._vcs_cache[vcs]:
                if vcs_path is False:
                    continue
                if VCS._is_sub_path(vcs_path, file_path):
                    return vcs_path

            return

    @staticmethod
    def _vcs_cache_write(vcs, vcs_path):
        if not vcs_path or VCS._is_sub_path(tempfile.gettempdir(), vcs_path):
            return False
        if vcs not in VCS._vcs_cache:
            VCS._vcs_cache.update({vcs: []})
        if vcs_path not in VCS._vcs_cache[vcs]:
            VCS._vcs_cache[vcs].append(vcs_path)
        return vcs_path

    @staticmethod
    def _save_to_file():
        if not sublime.cache_path():
            return
        path = os.path.join(sublime.cache_path(), VCS.CACHE_FILE_NAME)
        console.log("Saving VCS cache:", path)
        try:
            f = fopen(path, "w")
            f.write(sublime.encode_value({"_vcs": (VCS._vcs_cache)}, True))
            f.close()
        except:
            console.error("Could not save VCS cache:", path)

    @staticmethod
    def _read_from_file():
        path = os.path.join(sublime.cache_path(), VCS.CACHE_FILE_NAME)
        console.log("Reading VCS cache:", path)
        if os.path.exists(path):
            try:
                try:
                    f = fopen(path, "r")
                    data = sublime.decode_value(f.read())
                except:
                    console.error("Could not read VCS cache:", path)
                    data = None

            finally:
                f.close()

            if data:
                if "_vcs" in data:
                    VCS._vcs_cache = data["_vcs"]
            if data:
                if "_no_vcs" in data:
                    VCS._no_vcs_cache = data["_no_vcs"]
        return

    @staticmethod
    def _validate_cache():
        for vcs in VCS._vcs_cache:
            for vcs_path in VCS._vcs_cache[vcs][:]:
                sleep(VCS.THREAD_SLEEP_VALUE)
                if not os.path.exists(vcs_path) or not VCS._read_up(vcs, vcs_path):
                    VCS._vcs_cache[vcs].remove(vcs_path)
                    console.log("_vcs_cache invalid:", vcs, vcs_path)
                else:
                    console.log("_vcs_cache valid:", vcs, vcs_path)

        for vcs in VCS._no_vcs_cache:
            for vcs_path in VCS._no_vcs_cache[vcs][:]:
                sleep(VCS.THREAD_SLEEP_VALUE)
                if not os.path.exists(vcs_path) or VCS._read_up(vcs, vcs_path):
                    VCS._no_vcs_cache[vcs].remove(vcs_path)
                    console.log("_no_vcs_cache invalid:", vcs, vcs_path)
                else:
                    console.log("_no_vcs_cache valid:", vcs, vcs_path)
