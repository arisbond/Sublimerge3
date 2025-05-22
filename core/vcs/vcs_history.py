import sublime, os
from .vcs import VCS
from .git import Git
from .svn import SVN
from .mercurial import Mercurial
from ..promise import Promise
from ..utils import error_message
from ..menu import Menu, MenuItem

class VCSHistory:
    VcsClass = None

    def commits_for_view(self, view):
        return self._fetch_by_menu(view=view, file_name=None, callback=self._on_log_select_get_commit)

    def commits_for_file(self, file_name):
        return self._fetch_by_menu(view=None, file_name=file_name, callback=self._on_log_select_get_commit)

    def revision_for_view(self, view, commit=None):
        if commit is None:
            return self._fetch_by_menu(view=view, file_name=None, callback=self._on_log_select_get_revision_file)
        else:
            return self._fetch_by_revision(view.file_name(), commit)
            return

    def revision_for_file(self, file_name, commit=None):
        if commit is None:
            return self._fetch_by_menu(view=None, file_name=file_name, callback=self._on_log_select_get_commit)
        else:
            return self._fetch_by_revision(file_name, commit)
            return

    def _fetch_by_menu(self, view, file_name, callback):
        return self._fetch(view, file_name, self._log_to_menu, callback)

    def _fetch_by_revision(self, file_name, commit):

        def handler(view, file_name, callback):
            return self._fetch_revision(Promise(), file_name, commit)

        return self._fetch(None, file_name, handler, None)

    def _fetch_revision(self, promise, file_name, commit):
        self.VcsClass.cat(file_name, commit).then((lambda rev_file, commit: promise.resolve(rev_file, (self.VcsClass.unroot(file_name), self.VcsClass.format_commit(commit))))).otherwise(promise.reject)
        return promise

    def _fetch(self, view, file_name, handler, callback):
        vcs = VCS.which(view=view, file_name=file_name)
        root = VCS.root(vcs, view=view, file_name=file_name)
        if root:
            if vcs == VCS.GIT:
                self.VcsClass = Git
                return handler(view, file_name, callback)
            if vcs == VCS.SVN:
                pass
            self.VcsClass = SVN
            return handler(view, file_name, callback)
        else:
            if vcs == VCS.HG:
                self.VcsClass = Mercurial
                return handler(view, file_name, callback)
            return

    def _show_log_menu(self, view, promise, on_select):

        def handler(commit_stack):
            sublime.status_message("")
            if len(commit_stack) == 0:
                error_message("No history for file\n%s\nIs it versioned?" % view.file_name())
                return
            else:
                menu = Menu(on_select=(lambda sender, item: on_select(promise, view, item) or sender.destroy()), on_cancel=(lambda sender: sender.destroy()))
                seen = []
                for i in range(len(commit_stack)):
                    item = commit_stack[i]
                    if item["commit"] in seen:
                        continue
                    seen.append(item["commit"])
                    try:
                        previous = commit_stack[i + 1]
                    except:
                        previous = None

                    menu.add_item(MenuItem(caption=item["caption"], value={"selected": item, 
                     "previous": previous}))
                    previous = item

                menu.show()
                return

        return handler

    def _log_to_menu(self, view, file_name, handler):
        promise = Promise()
        self.VcsClass.log(file_name if file_name else view.file_name()).then(self._show_log_menu(view, promise, handler)).otherwise(promise.reject)
        return promise

    def _on_log_select_get_revision_file(self, promise, view, item):
        selected = item.get_value()["selected"]
        self._fetch_revision(promise, selected["file"], selected["commit"])

    def _on_log_select_get_commit(self, promise, view, item):
        promise.resolve(item.get_value()["selected"], item.get_value()["previous"])
