import sublime, sys, traceback, re

def show_confirm(exc):
    st_ver = 2
    if sublime.version() == "" or int(sublime.version()) >= 3000:
        st_ver = 3
    try:
        if st_ver == 3:
            pc_version = sys.modules["Package Control"].package_control.__version__
        else:
            pc_version = sys.modules["package_control"].__version__
    except:
        pc_version = None

    if sublime.ok_cancel_dialog("Sublimerge\n\nLoading error occured.\n\nIf you just installed or upgraded Sublimerge, please restart Sublime Text to check if the error still persists.\n\nPress `OK` if the error still persists after restart."):
        if pc_version is None or pc_version and sublime.ok_cancel_dialog("Sublimerge\n\nPlease make sure you have the latest Package Control installed. Older versions may corrupt Sublimerge package.\n\nPress `OK` if you have the latest Package Control."):
            errdata = "Sublimerge\n\nThe following information will be submitted:\n\n- Error description (including stack trace)\n- Operating system version\n- Sublimerge version\n- Sublime Text version\n- Python version"
            errdata += "\n- Package Control version" if pc_version else ""
            errdata += "\n- Your e-mail (you will be asked later)\n\nWould you like to send error report now?"
            if sublime.ok_cancel_dialog(errdata):

                def canceled_report():
                    sublime.error_message("Sublimerge\n\nReport submission cancelled")

                def send_report(email=None):
                    is_email = email and re.match("^.+@.+$", email)
                    if is_email or not is_email and not sublime.ok_cancel_dialog("Sublimerge\n\nYou did not provide e-mail address. If the problem is related to your system, I will not be able to contact and help you.\n\nPress `OK` to enter e-mail or `Cancel` to submit report anyway."):
                        try:
                            from core.metadata import PROJECT_VERSION
                        except:
                            try:
                                from .core.metadata import PROJECT_VERSION
                            except:
                                PROJECT_VERSION = "?"

                        body = "Reporter: %s\n\nOS: %s (%s) %s\nST: %s\nSM: %s\nPC: %s\nPY: %s\n\n%s" % (
                         email or "Not provided",
                         sublime.platform(),
                         sublime.arch(),
                         str(sys.getwindowsversion()) if sublime.platform() == "windows" else "",
                         sublime.version(),
                         PROJECT_VERSION,
                         pc_version or "Not found",
                         sys.version,
                         exc)
                        try:
                            if st_ver == 3:
                                import http.client
                                conn = http.client.HTTPConnection("www.sublimerge.com", 80)
                                conn.request("PUT", "/crashreport/", body)
                                resp = conn.getresponse()
                                if resp.status != 200:
                                    raise Exception("HTTP Error %d: %s" % (resp.status, resp.reason))
                            else:
                                import urllib2
                                opener = urllib2.build_opener(urllib2.HTTPHandler)
                                request = urllib2.Request("http://www.sublimerge.com/crashreport/", data=body)
                                request.add_header("Content-Type", "text/plain")
                                request.get_method = lambda : "PUT"
                                opener.open(request)
                            sublime.error_message("Your report has been sent. Thank you!\n\nIf you want to see the sent report, please open Sublime console.")
                        except Exception as e:
                            sublime.error_message("Error sending report:\n\n%s" % str(e))

                        print("[ERROR REPORT BEGIN]\n" + body + "\n[ERROR REPORT END]")
                    else:
                        ask_email()

                def ask_email():
                    sublime.active_window().show_input_panel("Please provide your e-mail. It will allow me to contact with you if the problem is related to your system:", "", send_report, None, canceled_report)
                    return

                ask_email()
    return


def report_error():
    exc = traceback.format_exc()
    print("Sublimerge: LOADING EXCEPTION BEGIN")
    print(exc)
    print("Sublimerge: LOADING EXCEPTION END")
    sublime.set_timeout((lambda : show_confirm(exc)), 3000)
