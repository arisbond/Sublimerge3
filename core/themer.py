import os, re, sublime, json
from .debug import console
from .settings import Settings

class Themer:
    THEME_FILE = os.path.join(sublime.packages_path(), "User", "Sublimerge")
    SUMMARY_THEME_FILE = os.path.join(sublime.packages_path(), "User", "SublimergeSummaryPanel")
    _settings = None
    _previous_theme_file = None
    _theme_file_ext = None

    @staticmethod
    def theme_file_ext():
        return Themer._theme_file_ext

    @staticmethod
    def summary_panel_theme_file(full_name=True):
        return ("Packages/User/" if full_name else "") + "SublimergeSummaryPanel" + Themer.theme_file_ext()

    @staticmethod
    def diff_view_theme_file(full_name=True):
        return ("Packages/User/" if full_name else "") + "Sublimerge" + Themer.theme_file_ext()

    @staticmethod
    def create(force=False):
        if not Themer._settings:
            Themer._settings = sublime.load_settings("Preferences.sublime-settings")
            Themer._settings.add_on_change("color_scheme", Themer.create)
        theme_file = Themer._settings.get("color_scheme")
        if not force and theme_file == Themer._previous_theme_file:
            return
        Themer._previous_theme_file = theme_file
        color_template = "<dict>\n\t\t\t<key>scope</key>\n\t\t\t<string>%s</string>\n\t\t\t<key>settings</key>\n\t\t\t<dict>\n\t\t\t\t<key>foreground</key>\n\t\t\t\t<string>%s</string>\n\t\t\t</dict>\n\t\t</dict>"
        theme_files = [
         theme_file,
         "Packages/Color Scheme - Default/" + os.path.basename(theme_file),
         "Packages/Color Scheme - Default/Monokai.sublime-color-scheme"]
        loaded = False
        for theme_file in theme_files:
            try:
                console.log("Trying to load base theme file:", theme_file)
                content = sublime.load_resource(theme_file)
                _, Themer._theme_file_ext = os.path.splitext(theme_file)
                console.log("Successfully loaded base theme file:", theme_file)
                loaded = True
                break
            except Exception as e:
                console.log("Could not load theme file:", theme_file, e)

        if not loaded:
            console.log("Could not load theme file")
            return
        try:
            isJSON = False
            try:
                content = json.loads(content)
                isJSON = True
            except Exception as e:
                pass

            to_insert = ""
            for key in Settings.color_keys:
                Settings.un_change(key)
                Settings.on_change(key, (lambda : Themer.create(True)))
                color_key = "sublimerge." + key
                color_value = Themer._resolve_color(Settings.get(key), content, isJSON)
                console.log("Writing color", color_value, "(%s)" % color_key)
                if isJSON:
                    content["rules"].append({"name": key, 
                     "scope": color_key, 
                     "foreground": color_value})
                else:
                    to_insert += "\n\t\t" + color_template % (color_key, color_value) + "\n\n\t"

            if isJSON:
                content = json.dumps(content)
            else:
                content = content.replace("</array>", to_insert + "</array>")
            path = Themer.THEME_FILE + Themer.theme_file_ext()
            cleanup = [
             Themer.THEME_FILE + ".tmTheme",
             Themer.THEME_FILE + ".sublime-color-scheme",
             Themer.SUMMARY_THEME_FILE + ".tmTheme",
             Themer.SUMMARY_THEME_FILE + ".sublime-color-scheme"]
            for v in cleanup:
                try:
                    if os.path.exists(v):
                        os.remove(v)
                except Exception as e:
                    pass

            console.log("Saving modified theme as:", path)
            f = open(path, "wb")
            f.write(str(content).encode("utf-8"))
            f.close()
            summary_panel_bg = Settings.get("summary_panel_background")
            if summary_panel_bg:
                if isJSON:
                    try:
                        content = json.loads(content)
                        content["globals"]["background"] = summary_panel_bg
                        content = json.dumps(content)
                    except Exception as e:
                        console.log("Could not set summary panel background color:", e)

                else:
                    content = re.sub("(<key>background</key>\\s*<string>\\s*)([^<]+)(\\s*</string>)", "\\1" + summary_panel_bg + "\\3", content)
            path = Themer.SUMMARY_THEME_FILE + Themer.theme_file_ext()
            console.log("Saving modified theme as:", path)
            f = open(path, "wb")
            f.write(str(content).encode("utf-8"))
            f.close()
        except Exception as e:
            print(e)
            console.log("Failed", e)

    @staticmethod
    def force_reload():
        path = Themer.THEME_FILE + Themer.theme_file_ext()
        f = open(path, "rb")
        content = f.read()
        f.close()
        f = open(path, "wb")
        f.write(content)
        f.close()

    @staticmethod
    def _resolve_color(color, content, isJSON):
        if color.startswith("#"):
            return color
        tries = ["foreground", "background"]
        if isJSON:
            for item in content["rules"]:
                if item["scope"] == color:
                    for key in tries:
                        if key in item:
                            return item[key]

                    continue

            return color
        regexp = re.compile("(<dict>\\s*<key>scope</key>\\s*<string>[^,<]*[,\\s]*" + re.escape(color) + "[^,<]*[,\\s]*</string>.*?</dict>)", re.S)
        scopes = regexp.findall(content)
        for scope in scopes:
            match = re.search("<key>(" + "|".join(tries) + ")</key>\\s*<string>(.*)</string>", scope)
            if match:
                return match.group(2)

        return color
