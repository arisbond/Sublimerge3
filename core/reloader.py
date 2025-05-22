import sys, imp, sublime, zipimport
from threading import Thread
from os.path import exists, join
from .metadata import PROJECT_NAME
from .task_manager import TaskManager
from .vcs.vcs import VCS
from .snapshots import Snapshots
from .settings import Settings
from .themer import Themer
from .task import Task
from .unpacker import unpack
from .linsp import LInsp
from .macros import Macros
from .startup_restore import StartupRestore
from .debug import console

class Reloader:
    _delayed_tasks = TaskManager(3000)
    _immediate_tasks = TaskManager(500)

    @staticmethod
    def reload():
        console.log("Reloading Sublimerge")
        try:
            StartupRestore.initialize()
            reload_modules = [
             'vendor', 
             'core', 
             'commands', 'core.lines', 
             'core.renderers', 
             'core.diff', 
             'core.window.text.behaviors', 
             'core.window.text', 
             'core.window.directories.behaviors', 
             'core.window.directories', 
             'core.window.view', 
             'core.window', 
             'core.vcs']
            skip_modules = [
             "core.settings", "core.Reloader"]
            imp.reload(sys.modules[PROJECT_NAME + ".core.metadata"])
            for i in range(0, 2):
                for submodule in reload_modules:
                    submodule_path = PROJECT_NAME + "." + submodule
                    for name in dir(sys.modules[submodule_path]):
                        subsubmodule_path = submodule_path + "." + name
                        if name[0:2] != "__" and subsubmodule_path not in skip_modules:
                            imp.reload(sys.modules[subsubmodule_path])
                            continue

            Reloader._delayed_tasks.remove(Reloader._initialize)
            Reloader._delayed_tasks.add(Reloader._initialize)
            Reloader._immediate_tasks.remove(Reloader._initialize_theme)
            Reloader._immediate_tasks.add(Reloader._initialize_theme)
            Reloader._immediate_tasks.remove(Reloader._unpack_package)
            Reloader._immediate_tasks.add(Reloader._unpack_package)
            Reloader._immediate_tasks.remove(LInsp.r_init)
            Reloader._immediate_tasks.add(LInsp.r_init)
        except zipimport.ZipImportError as e:
            console.warn("ZipImportError while reloading Sublimerge", e)
        except Exception as e:
            console.error("Exception while reloading Sublimerge", e)
            raise

    @staticmethod
    def _initialize():
        Reloader._disable_conflicting_packages()
        VCS.initialize()
        Snapshots.initialize()
        Macros.initialize()

    @staticmethod
    def _initialize_theme():
        Task.spawn(Themer.create)

    @staticmethod
    def _unpack_package():
        Task.spawn(unpack)

    @staticmethod
    def _disable_conflicting_packages():
        packages_to_disable = ["Sublimerge 2", "Sublimerge Pro"]
        settings = sublime.load_settings("Preferences.sublime-settings")
        ignored_packages = settings.get("ignored_packages")
        for package in packages_to_disable:
            path_package = join(sublime.installed_packages_path(), "%s.sublime-package" % package)
            path_directory = join(sublime.packages_path(), package)
            if exists(path_package) or exists(path_directory):
                if package not in ignored_packages:
                    sublime.error_message("Packages %s and %s can't be enabled together.\n\n%s have been disabled in order to avoid conflicts.\n\nPlease save your work and restart Sublime Text to complete the process." % (package, PROJECT_NAME, package))
                    ignored_packages.append(package)
                    settings.set("ignored_packages", ignored_packages)
                    sublime.save_settings("Preferences.sublime-settings")
                    return
                continue
