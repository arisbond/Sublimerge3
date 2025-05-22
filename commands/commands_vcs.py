import sublime, os, re
from ..core.window.text.diff_window import DiffWindow2
from ..core.menu import Menu, MenuItem
from ..core.diff_file import LocalFile, ViewFile
from ..core.vcs.vcs import VCS
from ..core.settings import Settings
from ..core.debug import console
from ..core.vcs.git import Git
from ..core.vcs.svn import SVN
from ..core.menu import Menu, MenuItem
from ..core.utils import truncate, error_message
from ..core.vcs.vcs_history import VCSHistory
from .base_commands import _BaseEditorCommand

class _BaseVcsCommand(_BaseEditorCommand):
    VcsClass = None

    def __init__(self, *args):
        _BaseEditorCommand.__init__(self, *args)
        self._history = VCSHistory()

    def is_visible(self, index=-1, group=-1):
        view = self._get_view(index, group)
        return VCS.which(view=view) is not None


class SublimergeCompareToRevisionCommand(_BaseVcsCommand):

    def description(self, index=-1, group=-1):
        return "Compare to Revision..."

    def _compare(self, view, commit_file, commit):
        DiffWindow2.spawn(LocalFile(path=commit_file, temporary=True, read_only=True, title=os.path.basename(commit[0]) + " @ " + commit[1]), ViewFile(view=view))

    def run(self, index=-1, group=-1):
        view = self._get_view(index, group)
        self._history.revision_for_view(view).then((lambda file_name, commit: self._compare(view, file_name, commit))).otherwise(error_message)


class _BaseRevisionsCompareMixin:

    def _compare_rev(self, src_files, commits):
        loaded = []
        if os.path.dirname(commits[0][0]) == os.path.dirname(commits[1][0]):
            file_a = os.path.basename(commits[0][0])
            file_b = os.path.basename(commits[1][0])
        else:
            file_a = commits[0][0][1:]
            file_b = commits[1][0][1:]
        DiffWindow2.spawn(LocalFile(path=src_files[0], temporary=True, read_only=True, title=file_a + " @ " + commits[0][1]), LocalFile(path=src_files[1], temporary=True, read_only=True, title=file_b + " @ " + commits[1][1]))


class SublimergeCompareRevisionToRevisionCommand(_BaseVcsCommand, _BaseRevisionsCompareMixin):

    def description(self, index=-1, group=-1):
        return "Compare Revision to Revision..."

    def run(self, index=-1, group=-1):
        view = self._get_view(index, group)
        files = []
        commits = []

        def rev_loaded(file_name, commit):
            files.append(file_name)
            commits.append(commit)
            if len(files) < 2:
                get_rev()
            else:
                self._compare_rev(files, commits)

        def get_rev():
            self._history.revision_for_view(view).then(rev_loaded).otherwise(error_message)

        get_rev()


class SublimergeShowChangesInRevisionCommand(_BaseVcsCommand, _BaseRevisionsCompareMixin):

    def description(self, index=-1, group=-1):
        return "Show Changes Introduced in Revision..."

    def run(self, index=-1, group=-1):
        view = self._get_view(index, group)
        self._history.commits_for_view(view).then(self._load).otherwise(error_message)

    def _load(self, selected, previous):
        if previous is None:
            error_message("No previous commit to compare to")
            return
        else:
            files = []
            commits = []

            def rev_loaded(file_name, commit):
                files.append(file_name)
                commits.append(commit)
                if len(files) == 1:
                    self._history.revision_for_file(selected["file"], selected["commit"]).then(rev_loaded).otherwise(error_message)
                else:
                    self._compare_rev(files, commits)

            self._history.revision_for_file(previous["file"], previous["commit"]).then(rev_loaded).otherwise(error_message)
            return
