import sublime, time
from hashlib import sha1
from .window.view.collection import DiffViewCollection
from .settings import Settings

class Snapshots:
    _snapshots = {}
    _hashes = {}
    _NUM = 1

    @staticmethod
    def initialize():
        for window in sublime.windows():
            for view in window.views():
                if not DiffViewCollection.find(view):
                    Snapshots.create_auto(view, "File Open")
                    continue

    @staticmethod
    def status_message(view, text):
        view.set_status("snapshots", text)
        sublime.set_timeout((lambda : view.erase_status("snapshots")), 3000)

    @staticmethod
    def erase(view):
        try:
            Snapshots._snapshots[view.id()] = None
            Snapshots._hashes[view.id()] = None
        except:
            pass

        return

    @staticmethod
    def get_all(view):
        try:
            return Snapshots._snapshots[view.id()]
        except:
            pass

        return

    @staticmethod
    def has_any(view):
        return view.id() in Snapshots._snapshots

    @staticmethod
    def has_other_than(view):
        snapshots = Snapshots.get_all(view)
        if snapshots is None:
            return False
        else:
            h = Snapshots.hash(view)
            return h not in snapshots or len(snapshots.keys()) > 1

    @staticmethod
    def exists(view):
        h = Snapshots.hash(view)
        try:
            if Snapshots._snapshots[view.id()][h] is not None:
                return True
        except:
            pass

        return False

    @staticmethod
    def create_auto(view, prefix):
        if not Snapshots.exists(view):
            Snapshots.create(view, prefix + ", " + time.strftime(Settings.get("snapshots_date_format")))

    @staticmethod
    def get(view, hash):
        try:
            return Snapshots._snapshots[view.id()][hash]
        except:
            return

        return

    @staticmethod
    def restore(view, hash):
        item = Snapshots._snapshots[view.id()][hash]
        Snapshots.create_auto(view, "Before Revert to: " + item["name"])
        sel = []
        pos = view.viewport_position()
        [sel.append([region.begin(), region.end()]) for region in view.sel()]
        view.run_command("sublimerge_view_replace", {"begin": 0, 
         "end": (view.size()), 
         "text": (item["src"])})
        view.sel().clear()
        [view.sel().add(sublime.Region(region[0], region[1])) for region in sel]
        sublime.set_timeout((lambda : view.set_viewport_position(pos, False)), 200)
        Snapshots.status_message(view, "Reverted to Snapshot: " + item["name"])

    @staticmethod
    def create(view, name):
        h = Snapshots.hash(view)
        try:
            snapshots = Snapshots._snapshots[view.id()] or {}
        except:
            snapshots = {}

        snapshots.update({h: {"name": name, 
             "hash": h, 
             "src": (view.substr(sublime.Region(0, view.size()))), 
             "date": (time.strftime(Settings.get("snapshots_date_format")))}})
        Snapshots._snapshots.update({(view.id()): snapshots})
        Snapshots._NUM += 1
        try:
            _hashes = Snapshots._hashes[view.id()] or []
        except:
            _hashes = []

        _hashes.append(h)
        Snapshots._hashes.update({(view.id()): _hashes})
        Snapshots.status_message(view, "Created Snapshot: " + name)

    @staticmethod
    def get_next_name():
        return "Snapshot %d" % Snapshots._NUM

    @staticmethod
    def remove(view, hash):
        try:
            removed = Snapshots._snapshots[view.id()].pop(hash, None)
            for i in range(len(Snapshots._hashes)):
                if Snapshots._hashes[view.id()][i] == hash:
                    del Snapshots._hashes[view.id()][i]
                    break

            if len(Snapshots._snapshots[view.id()].keys()) == 0:
                Snapshots._snapshots.pop(view.id(), None)
            Snapshots.status_message(view, "Removed Snapshot: " + removed["name"])
            return True
        except:
            pass

        return False

    @staticmethod
    def replace(view, hash):
        try:
            item = Snapshots._snapshots[view.id()][hash]
            Snapshots.remove(view, hash)
            Snapshots.create(view, item["name"])
            return True
        except:
            pass

        return False

    @staticmethod
    def hash(view):
        src = view.substr(sublime.Region(0, view.size()))
        return sha1(src.encode("utf-8", "replace")).hexdigest()

    @staticmethod
    def get_menu_items(view, get_all=False):
        snapshots = Snapshots.get_all(view)
        self_h = Snapshots.hash(view)
        if snapshots is not None:
            qp_items = []
            for i in range(len(Snapshots._hashes[view.id()])):
                h = Snapshots._hashes[view.id()][i]
                if not get_all:
                    if h == self_h:
                        continue
                    item = snapshots[h]
                    yield (
                     item["name"], item["date"], item["hash"])

        return
