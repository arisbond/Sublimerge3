import sublime, os, sys, re

def console_log(*args):
    print("[Sublimerge]", *args)


class Settings:
    THREE_WAY_REMOTE_MERGED_LOCAL = 0
    THREE_WAY_REMOTE_LOCAL_MERGED = 1
    unimportant_regexp_compiled = None
    unimportant_regexp_compiled_multiline = None
    settings = None
    added_handler = False
    color_keys = [
     'diff_block_changed', 
     'diff_block_inserted', 
     'diff_block_deleted', 
     'diff_block_intraline_changed', 
     'diff_block_intraline_inserted', 
     'diff_block_intraline_deleted', 
     'diff_block_selected', 
     'diff_block_missing', 
     'diff_block_conflict']
    s = {"environment": {},  "date_format": "%a %b %d %H:%M:%S %Y", 
     "use_current_window": False, 
     "save_and_stay": True, 
     "__devel__": False, 
     "shell_fallback_encoding": "ascii", 
     "file_encoding_detection_strategy": "auto", 
     "debug": False, 
     "auto_select_first": True, 
     "same_syntax_only": True, 
     "intelligent_files_sort": True, 
     "macros_in_separate_menu": False, 
     "macros_in_command_palette": True, 
     "full_screen": False, 
     "toggle_menu": True, 
     "toggle_side_bar": True, 
     "toggle_minimap": False, 
     "compact_files_list": True, 
     "summary_panel": True, 
     "summary_panel_background": None, 
     "diff_view_allowed_commands": {},  "https_proxy": "", 
     "proxy_username": "", 
     "proxy_password": "", 
     "beyond_viewport_rendering": 0.25, 
     "diff_block_renderer": "gutter", 
     "diff_block_changed": "#FDECAC", 
     "diff_block_inserted": "#64BF0E", 
     "diff_block_deleted": "#F92672", 
     "diff_block_conflict": "#FF0000", 
     "diff_block_intraline_changed": "#FDECAC", 
     "diff_block_intraline_inserted": "#FDECAC", 
     "diff_block_intraline_deleted": "#FDECAC", 
     "diff_block_selected": "#75715E", 
     "diff_block_missing": "#75715E", 
     "intraline_analysis": True, 
     "intraline_changes_threshold": 60, 
     "intraline_combine_threshold": 3, 
     "intraline_style": "filled", 
     "intraline_unimportant_regexps": [],  "intraline_unimportant_style": "outlined", 
     "algorithm": "patience", 
     "ignore_whitespace": [],  "ignore_case": False, 
     "ignore_crlf": True, 
     "vcs_support": True, 
     "vcs_cache_enabled": True, 
     "vcs_cache_validate_on_startup": True, 
     "vcs_discovery_order": [
                             "git", "hg", "svn"], 
     "vcs_after_merge_cleanup": True, 
     "git_executable_path": "git", 
     "git_log_args": "--encoding=UTF-8 --no-color --no-decorate --follow", 
     "git_log_format": "%H\t%h\t%an <%ae>\t%ai\t%s", 
     "git_log_date_parse_format": "%Y-%m-%d %H:%M:%S %z", 
     "git_log_regexp": "^(?P<commit>.+)\t(?P<abbrev_commit>.+)\t(?P<author>.+)\t(?P<date_raw>.+)\t(?P<subject>.*)$", 
     "git_log_template": [
                          "${abbrev_commit} | ${subject}", "by ${author}", "${date}"], 
     "git_global_args": "-c color.ui=false", 
     "git_show_args": "", 
     "svn_executable_path": "svn", 
     "svn_log_args": "--stop-on-copy", 
     "svn_log_template": [
                          "${commit} | ${subject}", "by ${author}", "${date}"], 
     "svn_log_date_parse_format": "%Y-%m-%dT%H:%M:%S.%fZ", 
     "svn_cat_args": "", 
     "svn_global_args": "", 
     "hg_executable_path": "hg", 
     "hg_log_args": "--encoding=UTF-8", 
     "hg_log_format": "{node}\t{author}\t{date|isodate}\t{desc}", 
     "hg_log_date_parse_format": "%Y-%m-%d %H:%M %z", 
     "hg_log_regexp": "^(?P<commit>.+)\t(?P<author>.+)\t(?P<date_raw>.+)\t(?P<subject>.*)$", 
     "hg_log_template": [
                         "${abbrev_commit} | ${subject}", "by ${author}", "${date}"], 
     "hg_cat_args": "", 
     "hg_global_args": "", 
     "three_way_layout": 0, 
     "three_way_merged_height": 40, 
     "three_way_navigate_all": False, 
     "go_to_next_after_merge": False, 
     "view": {"line_numbers": False, 
              "word_wrap": False, 
              "highlight_line": True, 
              "draw_white_space": "all"}, 
     "start_swapped": False, 
     "scroll_sync_interval": 1, 
     "snapshots_on_open": True, 
     "snapshots_on_save": False, 
     "snapshots_in_menu": True, 
     "snapshots_date_format": "%d/%m/%Y %H:%M:%S", 
     "dir_compare_open_text_diff_in_new_window": False, 
     "dir_compare_ignore_dirs": [
                                 'RCS', 
                                 'CVS', 'tags', 
                                 '.git', '.svn', 
                                 '.hg'], 
     "dir_compare_ignore_files": [
                                  ".DS_Store", "Thumbs.db"], 
     "dir_compare_navigate_all": True, 
     "dir_merge_remove_unmatched": False}

    @staticmethod
    def load(file_type=None, force=False):
        if force or Settings.settings is None:
            Settings.unimportant_regexp_compiled_multiline = None
            Settings.unimportant_regexp_compiled = None
            Settings.settings = sublime.load_settings("Sublimerge 3.sublime-settings")
            if not Settings.added_handler:
                Settings.settings.add_on_change("reload", (lambda : Settings.load(force=True)))
                Settings.added_handler = True
            for name in Settings.s:
                if Settings.settings.has(name):
                    Settings.s[name] = Settings.settings.get(name)
                    continue

            for name in Settings.s["environment"]:
                os.environ[name] = Settings.s["environment"][name]

            syntax_specific = Settings.settings.get("syntax_specific", {})
            if syntax_specific:
                if file_type and file_type in syntax_specific:
                    for name in syntax_specific[file_type]:
                        try:
                            if isinstance(syntax_specific[file_type][name], dict):
                                for name2 in syntax_specific[file_type][name]:
                                    try:
                                        Settings.s[name][name2] = syntax_specific[file_type][name][name2]
                                    except:
                                        pass

                            else:
                                Settings.s[name] = syntax_specific[file_type][name]
                        except:
                            pass

            def re_compile(regexp, flags=0):
                try:
                    compiled = re.compile(regexp, flags)
                except Exception as e:
                    sublime.error_message("Sublimerge\nintraline_unimportant_regexps: " + str(e) + ":\n\n" + regexp)
                    return re.compile("^$")

                if compiled.groups == 0:
                    sublime.error_message("Sublimerge\nintraline_unimportant_regexps: No capturing groups found in regular expression:\n\n" + regexp)
                return compiled

            Settings.unimportant_regexp_compiled_multiline = list(map((lambda v: re_compile(v, re.MULTILINE)), Settings.get("intraline_unimportant_regexps")))
            Settings.unimportant_regexp_compiled = list(map((lambda v: re_compile(v)), Settings.get("intraline_unimportant_regexps")))
        return

    @staticmethod
    def on_change(key, cb):
        Settings.settings.add_on_change(key, cb)

    @staticmethod
    def un_change(key):
        Settings.settings.clear_on_change(key)

    @staticmethod
    def set(name, value):
        Settings.s.update({name: value})

    @staticmethod
    def get(name):
        Settings.load()
        return Settings.s[name]

    @staticmethod
    def get_unimportant_regexp_multiline():
        return Settings.unimportant_regexp_compiled_multiline

    @staticmethod
    def get_unimportant_regexp():
        return Settings.unimportant_regexp_compiled
