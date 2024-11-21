"""Copyright (c) Borys Forytarz. All rights reserved"""

from .core.reloader import Reloader
from .core.listener import *
from .core.error_reporter import report_error

from .commands.commands_sublimerge import *
from .commands.commands_diff import *
from .commands.commands_shell import *

def plugin_loaded():
    try:
        Reloader.reload() #reload everything
    except:
        report_error()
