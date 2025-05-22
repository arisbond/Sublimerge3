from collections import OrderedDict
from ....settings import Settings
from ....object import Object

class BehaviorStatusSettings:
    if Object.DEBUG:

        def __del__(self):
            Object.rem(self)

    def __init__(self):
        if Object.DEBUG:
            Object.add(self)
        self.on("diff_start", (lambda sender: self.refresh_status()))

    def refresh_status(self):
        settings = OrderedDict()
        settings.update({"ignore_crlf": "Ignore CR/LF"})
        settings.update({"ignore_case": "Ignore Case"})
        settings.update({"ignore_whitespace": "Ignore Whitespace"})
        settings.update({"intraline_analysis": "Intraline Analysis"})
        for i, setting in enumerate(settings):
            value = Settings.get(setting)
            if setting == "ignore_whitespace":
                if "begin" in value and "end" in value:
                    value = "All"
                elif "begin" in value:
                    value = "Line Begin"
                elif "end" in value:
                    value = "Line End"
                else:
                    value = "Off"
            else:
                value = "On" if value else "Off"
            self._set_status("status_%d" % i, settings[setting] + ": " + value)
