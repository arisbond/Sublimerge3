import sublime_plugin, os, sublime
from .vcs.vcs import VCS
from .reloader import Reloader
from .window.view.collection import DiffViewCollection
from .window.collection import DiffWindowCollection
from .metadata import PROJECT_NAME
from .snapshots import Snapshots
from .settings import Settings

class Listener(sublime_plugin.EventListener):

    def reload_plugin(self, view):
        try:
            if Settings.get("__devel__"):
                if view.file_name().index(PROJECT_NAME):
                    Reloader.reload()
                    path = os.path.join(sublime.packages_path(), PROJECT_NAME, "Sublimerge.py")
                    f = open(path, "r")
                    content = f.read()
                    f.close()
                    f = open(path, "w")
                    f.write(content)
                    f.close()
        except:
            pass

    def on_window_command(self, window, command, args):
        return self.handle_command(window.active_view(), command, args)

    def on_text_command(self, view, command, args):
        return self.handle_command(view, command, args)

    def handle_command(self, view, command, args):
        if not view:
            return
        else:
            diff_window = DiffWindowCollection.find(view.window())
            diff_view = DiffViewCollection.find(view)
            if command.startswith("sublimerge_"):
                return
            else:
                if not diff_window or not diff_view:
                    return

                def handle_show_panel(args):
                    if args["panel"] in ('find', 'replace'):
                        diff_window.on_show_panel(args["panel"])
                    elif args["panel"] in ('find_in_files', ):
                        return False

                allowed = [
                 'move_to', 
                 'drag_select', 
                 'select_all', 
                 'single_selection', 
                 'insert_snippet', 
                 'set_line_ending', 
                 'set_setting', 
                 'toggle_setting', 
                 'insert_best_completion', 
                 'move', 
                 'scroll_lines', 
                 'run_macro_file', 
                 'reindent', 
                 'indent', 
                 'unindent', 
                 'auto_complete', 
                 'hide_auto_complete', 
                 'commit_completion', 
                 'toggle_overwrite', 
                 'toggle_comment', 
                 'find_next', 
                 'copy_path', 
                 'open_dir', 
                 'open_terminal', 
                 'increase_font_size', 
                 'decrease_font_size', 
                 'next_view', 
                 'prev_view', 
                 'focus_neighboring_group']
                disallowed = {"toggle_setting": {"setting": [
                                                "word_wrap"]}}
                need_refresh = {"expand_tabs": "*", 
                 "unexpand_tabs": "*"}
                rewritten_in_read_only = {"cut": "copy"}
                forbidden_in_read_only = ('left_delete', 'right_delete', 'insert',
                                          'paste', 'paste_and_indent', 'cut')
                rewritten = {"undo": (lambda : diff_window.undo(diff_view) or False), 
                 "redo": (lambda : diff_window.redo(diff_view) or False), 
                 "soft_undo": (lambda : diff_window.undo(diff_view) or False), 
                 "soft_redo": (lambda : diff_window.redo(diff_view) or False), 
                 "redo_or_repeat": (lambda : diff_window.redo(diff_view) or False), 
                 "left_delete": (lambda : diff_window.left_delete(diff_view)), 
                 "right_delete": (lambda : diff_window.right_delete(diff_view)), 
                 "context_menu": (lambda : diff_view.on_context_menu(args)), 
                 "insert": (lambda : diff_view.get_view().sel()[0].size() == 0), 
                 "cut": (lambda : diff_window.cut(diff_view) or False), 
                 "copy": (lambda : diff_window.copy(diff_view) or False), 
                 "paste": (lambda : diff_window.paste(diff_view) or False), 
                 "paste_and_indent": (lambda : diff_window.paste(diff_view) or False), 
                 "insert": (lambda : diff_window.insert(diff_view) or False), 
                 "show_panel": (lambda : handle_show_panel(args)), 
                 "hide_panel": (lambda : diff_window.on_hide_panel()), 
                 "close": (lambda : diff_window.can_close()), 
                 "swap_line_down": (lambda : diff_window.swap_line_down(diff_view)), 
                 "swap_line_up": (lambda : diff_window.swap_line_up(diff_view))}
                noop = (
                 "noop", {"command": command,  "args": args})
                user_allowed = Settings.get("diff_view_allowed_commands")

                def is_allowed(command):
                    if command in disallowed:
                        for arg in args:
                            if arg in disallowed[command] and args[arg] in disallowed[command][arg]:
                                return False

                    if command in user_allowed:
                        if user_allowed[command] == "*":
                            return True
                        for arg in args:
                            if arg in user_allowed[command]:
                                if arg in user_allowed[command]:
                                    if user_allowed[command][arg] == "*":
                                        return True
                                    if args[arg] not in user_allowed[command][arg]:
                                        return False
                                continue

                    return command in allowed

                def needs_refresh(command):
                    if command in need_refresh:
                        for arg in args:
                            if need_refresh[command] == "*" or arg in need_refresh[command] and args[arg] in need_refresh[command][arg]:
                                return True

                    return False

                if diff_view.is_read_only():
                    if command in forbidden_in_read_only:
                        return noop
                    if command in rewritten_in_read_only:
                        command = rewritten_in_read_only[command]
                if needs_refresh(command):
                    pass
                return
            if command in rewritten:
                result = rewritten[command]()
                if result is False:
                    return noop
                return result
            else:
                is_allowed(command) or print("")
                print("Sublimerge blocked execution of the following command:", command, args if args else "")
                print("Commands that are not handled by Sublimerge or are not known to be safe,")
                print("must be blocked in order to make the diff view to work properly.")
                print("If you want to add support for this command, please take a look at `diff_view_allowed_commands` setting.")
                print("")
                return noop
            return

    def on_load(self, view):
        diff_view = DiffViewCollection.find(view)
        diff_window = DiffWindowCollection.find(view.window())
        if not diff_window:
            VCS.init_path(view.file_name())
            if Settings.get("snapshots_on_open"):
                Snapshots.create_auto(view, "File Open")

    def on_selection_modified(self, view):
        if view.settings().get("is_sublimerge_summary_panel"):
            view.sel().clear()
        else:
            DiffViewCollection.on_selection_modified(view)

    def on_close(self, view):
        DiffViewCollection.on_close(view)

    def on_activated(self, view):
        if not DiffViewCollection.on_activated(view):
            VCS.init_path(view.file_name())

    def on_deactivated(self, view):
        DiffViewCollection.on_deactivated(view)

    def on_modified(self, view):
        DiffViewCollection.on_modified(view)

    def on_pre_save(self, view):
        DiffViewCollection.on_pre_save(view)

    def on_post_save(self, view):
        self.reload_plugin(view)
        if not DiffViewCollection.on_post_save(view):
            VCS.init_path(view.file_name())
            if Settings.get("snapshots_on_save"):
                Snapshots.create_auto(view, "File Save")
