import shlex, re, sublime, os
from datetime import datetime
from ..shell_thread import ShellThread
from ..settings import Settings
from ..utils import create_suffixed_tmpfile_path, error_message, template, decode, relative_date
from ..promise import Promise
from ..xml import XML
from .vcs import VCS

class SVN:

    @classmethod
    def unroot(self, path):
        return VCS.unroot(path, VCS.SVN)

    @classmethod
    def format_commit(self, commit):
        return commit

    @classmethod
    def log(self, file_name):
        promise = Promise()
        lines = []
        commit_stack = []

        def on_success():
            xml = XML()
            xml.load_string("\n".join(lines))
            date_parse_format = Settings.get("svn_log_date_parse_format")
            date_user_format = Settings.get("date_format")
            for entry in xml.query("/log/logentry/*"):
                date = decode(entry.query("/date").text())
                try:
                    date_parsed = datetime.strptime(date, date_parse_format)
                except:
                    date_parsed = None

                params = {"commit": (decode(entry.get_attribute("revision"))), 
                 "author": (decode(entry.query("/author").text())), 
                 "date": (relative_date(date_parsed) if date_parsed else date), 
                 "date_raw": date, 
                 "date_user": (date_parsed.strftime(date_user_format) if date_parsed else date), 
                 "subject": (decode(entry.query("/msg").text()))}
                commit_stack.append({"caption": (template(Settings.get("svn_log_template"), params)), 
                 "commit": (params["commit"]), 
                 "file": file_name})

            if len(commit_stack) == 0:
                return False
            else:
                promise.resolve(commit_stack)
                return True

        sp = os.path.split(file_name)
        args = shlex.split(Settings.get("svn_global_args")) + ["log", "--xml"] + shlex.split(Settings.get("svn_log_args")) + ["--", sp[1]]
        thread = ShellThread(command=[
         Settings.get("svn_executable_path")] + args, directory=sp[0], on_each_line=(lambda line: lines.append(line)), on_success=(lambda *args: on_success() or promise.reject("\n".join(lines) or "No log for file. Is it versioned?")), on_failure=(lambda exit_code, errors: promise.reject("Error retrieving log.\n%s\nExit code: %d" % ("\n" + errors + "\n" if errors else "", exit_code))))
        thread.start()
        return promise

    @classmethod
    def cat(self, file_name, commit):
        promise = Promise()
        sp = os.path.split(file_name)
        args = shlex.split(Settings.get("svn_global_args")) + ["cat"] + shlex.split(Settings.get("svn_cat_args")) + ["./%s@%s" % (sp[1], commit)]
        output_file = create_suffixed_tmpfile_path(file_name)
        thread = ShellThread(command=[
         Settings.get("svn_executable_path")] + args, directory=sp[0], output_file=output_file, on_success=(lambda *args: promise.resolve(output_file, commit)), on_failure=(lambda exit_code, errors: promise.reject("Error retrieving file.\n%s\nExit code: %d" % ("\n" + errors + "\n" if errors else "", exit_code))))
        thread.start()
        return promise
