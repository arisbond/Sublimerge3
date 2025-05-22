import os, threading, sublime, shutil
from filecmp import dircmp
from ...settings import Settings
from ...utils import file_matches_list, error_message

class FileOps:

    def __init__(self):
        self._ignored_dirs = Settings.get("dir_compare_ignore_dirs")
        self._ignored_files = Settings.get("dir_compare_ignore_files")
        self._to_be_deleted = []

    def run(self, names, paths, progress_callback):
        self._to_be_deleted = []
        source_path, target_path = paths
        ops = []
        for v in names:
            source, target = v
            if source is None:
                ops += self._delete(os.path.join(target_path, target))
            elif target is None:
                ops += self._create(os.path.join(source_path, source), target_path)
            else:
                ops += self._overwrite(os.path.join(source_path, source), os.path.join(target_path, source))

        self._commit(ops, progress_callback)
        return

    def _delete(self, path):
        operations = []
        if os.path.isdir(path):
            roots = []
            for root, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    operations.append(("D", os.path.join(root, filename)))

                roots.append(root)

            for root in reversed(roots):
                operations.append(("D", root))

        else:
            operations.append(("D", path))
        return operations

    def _create_path(self, root, source, target):
        return os.path.join(target, root[len(source) + 1:])

    def _is_ignored_dir(self, name):
        name = os.path.basename(name)
        return name in self._ignored_dirs

    def _is_ignored_file(self, name):
        return file_matches_list(name, self._ignored_files)

    def _filter_ignored_dirs(self, dirnames):
        for ignored in self._ignored_dirs:
            if ignored in dirnames:
                dirnames.remove(ignored)
                continue

    def _filter_ignored_files(self, filenames):
        for filename in filenames[:]:
            if self._is_ignored_file(filename):
                filenames.remove(filename)
                continue

    def _iterate(self, path):
        for root, dirnames, filenames in os.walk(path):
            if self._is_ignored_dir(root):
                continue
            self._filter_ignored_dirs(dirnames)
            self._filter_ignored_files(filenames)
            yield (
             root, dirnames, filenames)

    def _create(self, source, target):
        target = os.path.join(target, os.path.basename(source))
        operations = []
        if os.path.isdir(source):
            if self._is_ignored_dir(source):
                return operations
            for root, dirnames, filenames in self._iterate(source):
                target_dir = self._create_path(root, source, target)
                operations.append(("MKD", target_dir))
                for filename in filenames:
                    operations.append(("CP", (os.path.join(root, filename), os.path.join(target_dir, filename))))

        elif not self._is_ignored_file(source):
            operations.append(("CP", (source, target)))
        return operations

    def _overwrite(self, source, target):
        operations = []
        if os.path.isdir(source) and os.path.isdir(target):
            if self._is_ignored_dir(source):
                return operations
            dc = dircmp(source, target, ignore=Settings.get("dir_compare_ignore_dirs"))
            for name in dc.left_only:
                operations += self._create(os.path.join(source, name), target)

            for name in dc.diff_files:
                operations += self._create(os.path.join(source, name), target)

            for name in dc.common_dirs:
                operations += self._overwrite(os.path.join(source, name), os.path.join(target, name))

            remove = Settings.get("dir_merge_remove_unmatched")
            for name in dc.right_only:
                if remove:
                    operations += self._delete(os.path.join(target, name))
                elif not self._is_ignored_file(name):
                    self._to_be_deleted.append(os.path.join(target, name))
                    continue

        else:
            operations.append(("CP", (source, target)))
        return operations

    def _copyfile(self, src, dst):
        if os.path.islink(src):
            linkto = os.readlink(src)
            os.symlink(linkto, dst)
        else:
            shutil.copy(src, dst)

    def _commit(self, operations, progress_callback):
        total = len(operations)
        failed = []
        for i in range(0, total):
            op, path = operations[i]
            success = False
            try:
                if op == "D":
                    if os.path.isdir(path):
                        os.rmdir(path)
                    else:
                        os.remove(path)
                elif op == "MKD":
                    os.mkdir(path)
                elif op == "CP":
                    self._copyfile(path[0], path[1])
                success = True
            except Exception as e:
                failed.append((operations[i], e))

            progress_callback(float(i + 1) / float(total))

        if len(failed) > 0:
            error_message("Some file operations failed. Please open your console for more information.")
            for fail in failed:
                print("Failed: ", fail)

        else:
            count = len(self._to_be_deleted)
        if count > 0:
            limit = 10
            if count > limit:
                msg_and_more = " (and %d more)" % (count - limit)
            else:
                msg_and_more = ""
            msg = "The following files%s were not deleted due to current settings:\n\n%s\n\nYou can remove them manually one by one." % (msg_and_more, "\n".join(self._to_be_deleted[0:limit]))
            error_message(msg)
