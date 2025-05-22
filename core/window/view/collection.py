import gc, sublime
from ...promise import Promise

class DiffViewCollection:
    GC_AFTER_MODIFIED_DEFER = 500
    _diff_views = []
    _gc_promise = None

    @staticmethod
    def add(diff_view):
        DiffViewCollection._diff_views.append(diff_view)

    @staticmethod
    def find(sublime_view):
        for diff_view in DiffViewCollection._diff_views:
            try:
                if diff_view.is_destroyed():
                    DiffViewCollection._diff_views.remove(diff_view)
                elif sublime_view.id() == diff_view.get_view().id():
                    return diff_view
            except:
                pass

        return False

    @staticmethod
    def remove(diff_view):
        try:
            DiffViewCollection._diff_views.remove(diff_view)
        except:
            pass

    @staticmethod
    def on_close(view):
        diff_view = DiffViewCollection.find(view)
        if diff_view:
            try:
                DiffViewCollection._diff_views.remove(diff_view)
            except:
                pass

            diff_view.on_close()
            return True
        return False

    @staticmethod
    def on_selection_modified(view):
        diff_view = DiffViewCollection.find(view)
        if diff_view:
            diff_view.on_selection_modified()
            return True
        return False

    @staticmethod
    def on_activated(view):
        diff_view = DiffViewCollection.find(view)
        if diff_view:
            diff_view.on_focus()
            return True
        return False

    @staticmethod
    def on_deactivated(view):
        diff_view = DiffViewCollection.find(view)
        if diff_view:
            diff_view.on_blur()
            return True
        return False

    @staticmethod
    def on_modified(view):
        diff_view = DiffViewCollection.find(view)
        if diff_view and not view.command_history(0, True)[0].startswith("sublimerge"):
            diff_view.on_modified()
            DiffViewCollection._schedule_gc()
            return True
        return False

    @staticmethod
    def _schedule_gc():
        if DiffViewCollection._gc_promise:
            DiffViewCollection._gc_promise.reject()
        DiffViewCollection._gc_promise = promise = Promise().then(gc.collect)
        sublime.set_timeout((lambda : promise.resolve()), DiffViewCollection.GC_AFTER_MODIFIED_DEFER)

    @staticmethod
    def on_pre_save(view):
        diff_view = DiffViewCollection.find(view)
        if diff_view:
            diff_view.on_pre_save()
            return True
        return False

    @staticmethod
    def on_post_save(view):
        diff_view = DiffViewCollection.find(view)
        if diff_view:
            diff_view.on_post_save()
            return True
        return False
