import shlex, re, sublime, os
from datetime import datetime
from ..shell_thread import ShellThread
from ..settings import Settings
from ..utils import create_suffixed_tmpfile_path, error_message, template, decode, relative_date
from ..promise import Promise
from ..vcs.vcs import VCS

class Git:

    @classmethod
    def unroot(self, path):
        return VCS.unroot(path, VCS.GIT)

    @classmethod
    def format_commit(self, commit):
        return commit[:7]

    @classmethod
    def log(self, file_name):
        promise = Promise()
        commit_stack = []
        output_stack = []
        try:
            regexp = re.compile(Settings.get("git_log_regexp"))
        except Exception as e:
            promise.reject("%s:\n\n%s" % (str(e), Settings.get("git_log_regexp")))
            return promise

        date_parse_format = Settings.get("git_log_date_parse_format")
        date_user_format = Settings.get("date_format")

        def add_commit_stack(line):
            line = decode(line).strip()
            if line.startswith("log:"):
                match = re.match(regexp, line[4:]).groupdict()
                if match:
                    if "date_raw" not in match:
                        promise.reject("git_log_regexp must contain a `date_raw` matching group")
                        return
                    if "commit" not in match:
                        promise.reject("git_log_regexp must contain a `commit` matching group")
                        return
                    try:
                        date_parsed = datetime.strptime(match["date_raw"], date_parse_format)
                    except:
                        date_parsed = None

                    match.update({"date": (relative_date(date_parsed) if date_parsed else match["date_raw"]), 
                     "date_user": (date_parsed.strftime(date_user_format) if date_parsed else match["date_raw"])})
                    try:
                        caption = template(Settings.get("git_log_template"), match)
                        commit_stack.append({"caption": caption, 
                         "commit": (match["commit"]), 
                         "file": file_name})
                    except Exception as e:
                        promise.reject(str(e))

                else:
                    output_stack.append(line)
            elif line:
                if commit_stack:
                    commit_stack[-1].update({"file": (os.path.join(VCS.root(VCS.GIT), line))})
            return

        sp = os.path.split(file_name)
        args = shlex.split(Settings.get("git_global_args")) + ["log"] + shlex.split(Settings.get("git_log_args")) + ["--name-only"] + ["--pretty=format:log:%s" % Settings.get("git_log_format"), "--", sp[1]]
        thread = ShellThread(command=[
         Settings.get("git_executable_path")] + args, directory=sp[0], on_each_line=add_commit_stack, on_success=(lambda *args: promise.resolve(commit_stack) if len(commit_stack) > 0 else promise.reject("\n".join(output_stack) or "No log for file. Is it versioned?")), on_failure=(lambda exit_code, errors: promise.reject("Error retrieving log.\n%s\nExit code: %d" % ("\n" + errors + "\n" if errors else "", exit_code))))
        thread.start()
        return promise

    @classmethod
    def cat(self, file_name, commit):
        promise = Promise()
        sp = os.path.split(file_name)
        args = shlex.split(Settings.get("git_global_args")) + ["show"] + shlex.split(Settings.get("git_show_args")) + ["%s:%s" % (commit, VCS.unroot(file_name, VCS.GIT))]
        output_file = create_suffixed_tmpfile_path(file_name)
        thread = ShellThread(command=[
         Settings.get("git_executable_path")] + args, directory=VCS.root(VCS.GIT, file_name=file_name), output_file=output_file, on_success=(lambda *args: promise.resolve(output_file, commit)), on_failure=(lambda exit_code, errors: promise.reject("Error retrieving file.\n%s\nExit code: %d" % ("\n" + errors + "\n" if errors else "", exit_code))))
        thread.start()
        return promise
