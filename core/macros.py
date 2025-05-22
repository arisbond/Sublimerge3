import sublime, re, os, tempfile, copy, json
from .vcs.vcs import VCS
from .vcs.vcs_history import VCSHistory
from .menu import Menu, MenuItem
from .window.text.diff_window import DiffWindow2, DiffWindow3
from .diff_file import LocalFile
from .settings import Settings
from .debug import console
from .utils import cmp_to_key, shell_cmd, fopen
from .task import Task

class MacroException(Exception):
    pass


class UndefinedVariableException(MacroException):

    def __init__(self, variable):
        super(UndefinedVariableException, self).__init__("Use of undefined variable: %s" % variable)


class UndefinedArgumentException(MacroException):

    def __init__(self, variable):
        super(UndefinedArgumentException, self).__init__("Use of undefined argument: %s" % variable)


class UndefinedModifierException(MacroException):

    def __init__(self, modifier):
        super(UndefinedModifierException, self).__init__("Call to undefined modifier: %s" % modifier)


class NoArgumentsException(MacroException):

    def __init__(self, modifier):
        super(NoArgumentsException, self).__init__("Empty arguments list")


class RegexpSyntaxException(MacroException):

    def __init__(self, regexp, error):
        super(RegexpSyntaxException, self).__init__("%s\n\n%s" % (error, regexp))


class CurrentVars:

    def FILE(self):
        view = sublime.active_window().active_view()
        if view is not None:
            return view.file_name() or ""
        else:
            return ""

    def FILE_NAME(self):
        file_path = self.FILE()
        return os.path.split(file_path)[1]

    def FILE_DIR(self):
        file_path = self.FILE()
        return os.path.split(file_path)[0]

    def REPO_ROOT(self):
        return VCS.root(VCS.which())

    def TEMP_DIR(self):
        return tempfile.gettempdir()


class EnvVars:

    def TEMP_DIR(self):
        return tempfile.gettempdir()


class Modifiers:

    def basename(self, name):
        return os.path.basename(name)

    def dirname(self, name):
        return os.path.dirname(name)

    def ext(self, name):
        return os.path.splitext(name)[1]

    def repopath(self, name):
        root = os.path.join(VCS.root(VCS.which()), "")
        if name.startswith(root):
            name = name[len(root):]
        return name


variables = {}
arguments_stack = []
current_vars = CurrentVars()
env_vars = EnvVars()
modifiers = Modifiers()

def modify(text, placeholder, replacement):
    global modifiers
    mods = placeholder[1:-1].split("|")
    for i in range(1, len(mods)):
        if not hasattr(modifiers, mods[i]):
            raise UndefinedModifierException(mods[i])
        replacement = getattr(modifiers, mods[i])(replacement)

    return text.replace(placeholder, replacement)


def decode(txt):
    if not hasattr(txt, "decode"):
        return txt
    try:
        return txt.decode("utf-8", "replace")
    except:
        return txt


def replace_regexps(pattern, match):
    pattern = replace_vars(pattern)
    for repl in re.finditer("@(\\d+)", pattern):
        pattern = pattern.replace(repl.group(0), match.group(int(repl.group(1))) or "")

    return pattern


def config(path, config):
    parts = path.split(".")
    for part in parts:
        try:
            if re.match("^\\d+$", part):
                config = config(int(part))
            else:
                config = config[part]
        except:
            raise MacroException("Wrong path %s near %s at %s" % (path, part, config))

    return config


def variable(name, value=None):
    global variables
    if value is not None:
        variables.update({name: value})
    elif name in variables:
        return config(name, variables)
    raise UndefinedVariableException(variable)
    return


def replace_vars(text):

    def fn_var(text, fn_prefix, fn_name, var_str, vars_obj):
        try:
            value_fn = getattr(vars_obj, fn_name)
        except Exception as e:
            raise UndefinedVariableException(fn_prefix + fn_name)

        return modify(text, var_str, value_fn())

    def repl(text):
        for match in re.finditer("\\${([^:}]+:)?([^}]+)}", text):
            if match.group(1) == "CONFIG:":
                text = modify(text, match.group(0), Settings.get(match.group(2).split("|")[0]))
            elif match.group(1) == "CURRENT:":
                text = fn_var(text, match.group(1), match.group(2).split("|")[0], match.group(0), current_vars)
            elif match.group(1) == "ENV:":
                text = fn_var(text, match.group(1), match.group(2).split("|")[0], match.group(0), env_vars)
            elif match.group(1) == "ARG:":
                ln = len(arguments_stack)
                if ln > 0:
                    name = match.group(2).split("|")[0]
                    try:
                        value = config(name, arguments_stack[ln - 1])
                    except:
                        raise UndefinedArgumentException(name)

                    text = modify(text, match.group(0), value)
                else:
                    raise NoArgumentsException()
            elif match.group(1) is None:
                if match.group(2) == "git":
                    text = modify(text, match.group(0), Settings.get("git_executable_path") + " " + Settings.get("git_global_args"))
                elif match.group(2) == "svn":
                    text = modify(text, match.group(0), Settings.get("svn_executable_path") + " " + Settings.get("svn_global_args"))
                elif match.group(2) == "hg":
                    text = modify(text, match.group(0), Settings.get("hg_executable_path") + " " + Settings.get("hg_global_args"))
                else:
                    try:
                        name = match.group(2).split("|")[0]
                        value = config(name, variables)
                    except Exception as e:
                        raise UndefinedVariableException(name)

                    text = modify(text, match.group(0), value)
                    continue

        return text

    if isinstance(text, list):
        for i in range(0, len(text)):
            text[i] = repl(text[i])

    elif isinstance(text, dict):
        for name in text:
            text[name] = replace_vars(text[name])

    else:
        text = repl(text)
    return text


def message(text):
    sublime.error_message("Sublimerge\n\n" + replace_vars(text))


def regexp_match(regexp_str, text):
    try:
        return re.match(regexp_str, text)
    except Exception as e:
        raise RegexpSyntaxException(regexp_str, str(e))


class Methods:
    proceed_callback = None

    def __init__(self, proceed_callback):
        self.proceed_callback = proceed_callback

    def log(self, text):
        print("Sublimerge: %s" % replace_vars(text))
        self.proceed()

    def proceed(self, stack=None):
        console.log("Proceed to next step")
        self.proceed_callback(stack)

    def define(self, **kwargs):
        for name in kwargs:
            variable(name, replace_vars(kwargs[name]))

        self.proceed()

    def history_panel(self, name, file):
        console.log("History Panel: " + name)
        file = replace_vars(file)
        vcs = VCS.root(VCS.which(file_name=file))
        if not os.path.exists(file):
            sublime.error_message("Sublimerge\n\nFile `%s` not found" % file)
            return
        if not vcs:
            sublime.error_message("Sublimerge\n\nFile `%s` is not versioned" % file)
            return

        def on_select(selected, previous):
            variable(name, selected["commit"])
            self.proceed()

        hp = VCSHistory()
        hp.commits_for_file(file).then(on_select)

    def quick_panel(self, name, source):
        console.log("Quick Panel: " + name, source)

        def on_select(sender, item):
            variable(name, item.get_value())
            self.proceed()

        if len(source) > 0:
            menu = Menu(on_select=on_select)
            for item in source:
                menu.add_item(MenuItem(caption=item["item"], value=item["value"]))

            menu.show()
        else:
            console.log("Empty source")

    def capture(self, execute, name="", value=None, regexp=None, greedy=False, empty_message="", continue_if_empty=False):
        console.log("Capture", execute)
        output = ""
        for line in execute.splitlines(int(greedy)):
            if regexp is not None:
                match = regexp_match(regexp, line)
                if match:
                    if value is not None:
                        output += replace_regexps(value, match)
                    else:
                        output += match.group(0)
                    if not greedy:
                        break
            else:
                output += line
                if not greedy:
                    break

        if output == "":
            if empty_message != "":
                message(empty_message)
                if not continue_if_empty:
                    return
        if name:
            variable(name, output)
        self.proceed()
        return

    def prompt(self, name, caption, default=""):
        console.log("Prompt: " + name)

        def callback(value):
            variable(name, replace_vars(value))
            self.proceed()

        sublime.active_window().show_input_panel(replace_vars(caption), replace_vars(default), callback, None, None)
        return

    def none(self, source=None, values=None):
        if source is not None:
            if values is not None:
                raise MacroException("Arguments `source` and `values` must not be combined together.")
        if source is not None:
            values = []
            for item in source:
                values.append(item["value"])

            return values
        else:
            if values is not None:
                for i in range(len(values)):
                    values[i] = replace_vars(values[i])

                return values
            raise MacroException("none/only: missing `source` or `values` argument")
            return

    def only(self, source=None, values=None):
        return self.none(source, values)

    def source(self, execute, item, reverse=False, none=None, only=None, alpha=False, empty_message=""):
        console.log("Source", execute, item)
        items = []
        unique = False
        if none is not None:
            if only is not None:
                raise MacroException("source: arguments `only` and `none` must not be combined together.")
        if "unique" in item.keys():
            unique = item["unique"]
        if "caption" not in item:
            raise MacroException("source: `caption` undefined")
        if "regexp" not in item:
            raise MacroException("source: `regexp` undefined")
        uniques = []
        for line in execute.splitlines(0):
            new_item = {"item": [],  "value": ""}
            m = regexp_match(item["regexp"], line)
            if m:
                for line in item["caption"]:
                    line = replace_regexps(line, m)
                    new_item["item"].append(line)

                new_item["value"] = replace_regexps(item["value"], m)
                if not unique or unique and new_item["value"] not in uniques:
                    if none is not None:
                        console.log("Filtering using `none`:", none)
                        if new_item["value"] in none:
                            continue
                    if only is not None:
                        console.log("Filtering using `only`:", none)
                        if new_item["value"] not in only:
                            continue
                    uniques.append(new_item["value"])
                    if reverse and not alpha:
                        items.insert(0, new_item)
                    else:
                        items.append(new_item)
                continue

        if alpha:
            items = sorted(items, key=cmp_to_key((lambda a, b: (a["item"][0].lower() > b["item"][0].lower()) - (a["item"][0].lower() < b["item"][0].lower()))))
            if reverse:
                items = items[::-1]
        if len(items) == 0:
            if empty_message != "":
                message(empty_message)
        return items

    def compare(self, left=None, right=None, theirs=None, base=None, mine=None, merged=None, execute=None):
        console.log("Compare", execute, left, right)
        active_view = sublime.active_window().active_view()
        if left is not None and right is not None:
            left["file"] = replace_vars(left["file"])
            right["file"] = replace_vars(right["file"])
            left_title = replace_vars(left["title"]) if "title" in left else None
            right_title = replace_vars(right["title"]) if "title" in right else None
            DiffWindow2.spawn(LocalFile(path=left["file"], temporary=left["temporary"], title=left_title, read_only=bool(left_title) or left["temporary"]), LocalFile(path=right["file"], temporary=right["temporary"], title=right_title, read_only=bool(right_title) or right["temporary"])).then((lambda *args: sublime.set_timeout(self.proceed, 100)))
        elif theirs is not None:
            if base is not None and mine is not None and merged is not None:
                theirs["file"] = replace_vars(theirs["file"])
                base["file"] = replace_vars(base["file"])
                mine["file"] = replace_vars(mine["file"])
                merged["file"] = replace_vars(merged["file"])
                theirs_title = replace_vars(theirs["title"]) if "title" in theirs else None
                mine_title = replace_vars(mine["title"]) if "title" in mine else None
                DiffWindow3.spawn(LocalFile(path=theirs["file"], temporary=theirs["temporary"], read_only=True, title=theirs_title), LocalFile(path=base["file"], temporary=base["temporary"], read_only=True), LocalFile(path=mine["file"], temporary=mine["temporary"], read_only=True, title=mine_title), LocalFile(path=merged["file"], temporary=merged["temporary"], read_only=False)).then((lambda : sublime.set_timeout(self.proceed, 100)))
        return

    def execute(self, command, directory="."):
        command = replace_vars(command)
        directory = replace_vars(directory)
        console.log("Execute", command, directory)
        out = ""
        for line in shell_cmd(command, directory, False):
            out += str(decode(line)) + "\n"

        return out

    def sublime_command(self, command, args={}):
        sublime.active_window().run_command(replace_vars(command), replace_vars(args))
        self.proceed()

    def ok_cancel_dialog(self, message, on_ok, ok_title="OK"):
        if sublime.ok_cancel_dialog(replace_vars("Sublimerge\n\n%s" % message), replace_vars(ok_title)):
            self.proceed(on_ok)

    def yes_no_cancel_dialog(self, message, on_yes, on_no, yes_title=None, no_title=None):
        button = sublime.yes_no_cancel_dialog(replace_vars("Sublimerge\n\n%s" % message), replace_vars(yes_title), replace_vars(no_title))
        if button == sublime.DIALOG_YES:
            self.proceed(on_yes)
        elif button == sublime.DIALOG_NO:
            self.proceed(on_no)


class Macro:
    name = None
    requires = None
    steps = None
    methods = None
    flow = None
    step_index = 0
    done_callback = None

    def __init__(self, settings):
        self.methods = Methods(self.proceed)
        self.name = replace_vars(settings["name"])
        self.steps = settings["steps"]
        self.requires = settings["requires"] if "requires" in settings else None
        self.platform = settings["platform"] if "platform" in settings else None
        self.functions = settings["functions"] if "functions" in settings else None
        return

    def is_enabled(self):
        return (self.requires is None or self.requires == VCS.which()) and (self.platform is None or isinstance(self.platform, list) and sublime.platform() in self.platform or sublime.platform() == self.platform)

    def is_visible(self):
        return self.is_enabled()

    def description(self):
        return self.name

    def execute(self, done_callback=None):
        self.done_callback = done_callback
        try:
            if len(self.steps) == 0:
                raise MacroException("Macro should contain at least one step")
            elif len(self.steps[self.step_index]) == 1:
                self.parse_settings(self.steps[self.step_index])
            else:
                raise MacroException("Exactly one directive in step allowed")
        except Exception as e:
            estr = e.__class__.__name__ + ": " + str(e)
            if not re.match("^Sublimerge\n\n", str(e)):
                sublime.error_message("Sublimerge: Macro runtime exception\n\n%s\n\n@step:%d" % (estr, self.step_index))
            import traceback
            print(traceback.format_exc())

    def proceed(self, stack=None):
        if stack:
            if not isinstance(stack, list):
                raise MacroException("Excpected list, %s given" % type(stack).__name__)
            m = Macro({"name": "",  "steps": stack})
            m.execute(self.proceed)
        elif self.step_index < len(self.steps) - 1:
            self.step_index += 1
            self.execute()
        elif self.done_callback:
            self.done_callback()

    def parse_settings(self, settings):
        to_be_called = None
        args = {}
        if isinstance(settings, dict):
            for name in settings:
                if hasattr(self.methods, name):
                    to_be_called = getattr(self.methods, name)
                    call_args = copy.deepcopy(settings[name])
                    if isinstance(call_args, dict):
                        args.update({name: (to_be_called(**self.parse_settings(call_args)))})
                    else:
                        args.update({name: (to_be_called(self.parse_settings(call_args)))})
                else:
                    args.update({name: (settings[name])})

            return args
        else:
            return settings
            return


class Macros:
    _settings = None
    _macros = None

    @classmethod
    def get_macros(self, reload=False):
        if reload:
            self._load()
        return self._macros or []

    @classmethod
    def initialize(self):
        self._load()
        Task.spawn(self._write_macros_commands)

    @classmethod
    def _load(self):
        console.log("Loading Macros")
        if not self._settings:
            self._settings = sublime.load_settings("Sublimerge Macros.sublime-settings")
            self._settings.add_on_change("macros_user", self.initialize)
        self._macros = []
        for macro_settings in self._settings.get("macros"):
            self._macros.append(Macro(macro_settings))

        macros_user = self._settings.get("macros_user")
        if macros_user is not None:
            for macro_settings in macros_user:
                self._macros.append(Macro(macro_settings))

        return

    @classmethod
    def _write_macros_commands(self):
        try:
            data = []
            if Settings.get("macros_in_command_palette"):
                for i, macro in enumerate(self._macros):
                    data.append({"caption": ("Sublimerge: " + macro.description()), 
                     "command": "sublimerge_macro", 
                     "args": {"run": i}})

            datastr = json.dumps(data, indent=4, separators=(',', ': '))
            path = os.path.join(sublime.packages_path(), "User", "Sublimerge Macros.sublime-commands")
            f = fopen(path, "w")
            f.write(datastr)
            f.close()
            console.log("Macros registered in Command Pallette")
        except Exception as e:
            console.error("Failed to register Macros in Command Pallette", e)
