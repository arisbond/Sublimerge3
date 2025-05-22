import inspect, time, re
from .settings import Settings
from .metadata import PROJECT_VERSION, PROJECT_NAME
from .utils import truncate

def stringify(val):
    if isinstance(val, tuple):
        return "(%s)" % ", ".join(stringify(v) for v in val)
    else:
        if isinstance(val, list):
            return "[%s]" % ", ".join(stringify(v) for v in val)
        if isinstance(val, dict):
            return "{%s}" % ", ".join(["%s: %s" % (k, stringify(val[k])) for k in val])
        if isinstance(val, str) or isinstance(val, bytes):
            val = str(val)
            val = val.replace("\r", "\\r")
            val = val.replace("\n", "\\n")
            return "'" + truncate(val, 100).replace("'", "\\'") + "'"
        return str(val)


def caller_name(skips):
    try:
        stack = inspect.stack()
        start = 0 + skips
        if len(stack) < start + 1:
            return ""
        else:
            parentframe = stack[start][0]
            args = inspect.getargvalues(parentframe)
            callargs = []
            all_args = args.args[:]
            if args.varargs:
                all_args.append(args.varargs)
            if args.keywords:
                all_args.append(args.keywords)
            for arg in all_args:
                if arg != "self":
                    val = args.locals[arg]
                    if arg == args.varargs:
                        arg = "*" + arg
                    elif arg == args.keywords:
                        arg = "**" + arg
                    callargs.append(arg + "=" + stringify(val))
                    continue

            name = []
            module = inspect.getmodule(parentframe)
            if module:
                name.append(module.__name__)
            if "self" in parentframe.f_locals:
                name.append(str(parentframe.f_locals["self"]))
            codename = parentframe.f_code.co_name
            if codename != "<module>":
                name.append(codename)
            del parentframe
            return ".".join(name[1:]) + "(" + ", ".join(callargs) + ")"
    except:
        return "???"


class console:
    _PATTERN = "%s[Sublimerge %s] [%s] [%f] %s\n\t@ %s"
    _time = time.time()
    _timers = []

    @staticmethod
    def reset_timer():
        console._time = time.time()
        console._timers = []

    @staticmethod
    def timer_begin(name=None):
        if Settings.get("debug"):
            console._timers.append({"name": name,  "begin": (time.time())})

    @staticmethod
    def timer_end():
        if Settings.get("debug"):
            try:
                timer = console._timers.pop()
                duration = time.time() - timer["begin"]
                message = "%s: %f" % (timer["name"], duration)
            except:
                message = "Could not measure: missing timer_begin() ?"

            console._print(len(console._timers), False, "TIMER", message)

    @staticmethod
    def log(*args):
        console._print(0, True, "LOG", *args)

    @staticmethod
    def error(*args):
        console._print(0, True, "ERROR", *args)

    @staticmethod
    def warn(*args):
        console._print(0, True, "WARN", *args)

    @staticmethod
    def _print(level, stack, logtype, *args):
        if Settings.get("debug"):
            callers = []
            number = 3
            if stack:
                while True:
                    caller = caller_name(number)
                    if not caller:
                        break
                    callers.append(caller)
                    number += 1

            level_str = "\t" * level
            msg = console._PATTERN % (level_str, PROJECT_VERSION, logtype, time.time() - console._time, " ".join(str(arg) for arg in args), ("\n\t" + level_str + "@ ").join(callers))
            msg = re.sub("<([^<>]+) object at (0x[^>]+)>", "<\\1 @ \\2>", msg).replace("<" + PROJECT_NAME + ".", "<")
            print(msg)
