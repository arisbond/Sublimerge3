import sublime, os, re, sys, threading, subprocess, shlex
from .debug import console
from .thread_progress import ThreadProgress
from .settings import Settings
from .utils import fopen

class ShellThread(threading.Thread):

    def __init__(self, command, directory, on_success=None, on_failure=None, on_each_line=None, progress_text="Running", output_file=None):
        self._command = command
        self._directory = directory
        self._on_success = on_success
        self._on_failure = on_failure
        self._on_each_line = on_each_line
        self._progress_text = progress_text
        self._output_file_path = output_file
        self._output_file = fopen(output_file, "wb") if output_file else None
        threading.Thread.__init__(self)
        return

    def _decode(self, txt):
        if not hasattr(txt, "decode"):
            return str(txt)
        try:
            return str(txt.decode("utf-8", "replace"))
        except:
            return str(txt)

    def run(self):
        ThreadProgress(self, self._progress_text)
        encodings = [
         None,
         sys.getfilesystemencoding(),
         Settings.get("shell_fallback_encoding")]
        tried = []
        thrown = None
        for encoding in encodings:
            try:
                command = [value.encode(encoding) for value in self._command] if encoding is not None else self._command
                command = " ".join(['"' + arg.replace('"', '\\"') + '"' if not re.match("^[a-zA-Z0-9_=.-]+$", arg) else arg for arg in command])
                directory = self._directory.encode(encoding) if encoding is not None else self._directory
                console.log("Run encoded (%s) shell command. Cwd: %s, Cmd: %s" % (encoding, directory, command))
                p = subprocess.Popen(command, stdout=self._output_file or subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, cwd=directory, shell=True)
                thrown = None
                break
            except (UnicodeEncodeError, LookupError) as thrown:
                tried.append(encoding)
                continue

        if thrown is not None:
            sublime.error_message("Sublimerge\n\nFailed to encode shell command (tried: %s). Consider setting `shell_fallback_encoding` to match your locale settings." % ", ".join(tried))
            raise thrown
        output, errors = p.communicate()
        console.log("Shell command finished with status:", p.returncode, errors)
        if p.returncode != 0 or errors:
            errors = self._decode(errors)
            if self._output_file_path:
                if os.path.exists(self._output_file_path):
                    try:
                        os.remove(self._output_file_path)
                    except:
                        pass

            if self._on_failure:
                self._on_failure(p.returncode, errors)
        else:
            output = self._decode(output)
        if self._on_each_line is not None:
            for line in output.splitlines():
                self._on_each_line(line)

        if self._output_file:
            p.wait()
            self._output_file.flush()
        if self._on_success:
            self._on_success(output)
        return
