import re, sublime, time, os, sys, uuid, platform, json, codecs, traceback
try:
    from urllib2 import urlopen, build_opener, ProxyHandler
except:
    from urllib.request import urlopen, build_opener, ProxyHandler

from hashlib import sha1
from webbrowser import open_new_tab as browser_open
from base64 import decodestring as decode64
from base64 import encodestring as encode64
from .metadata import PROJECT_VERSION, PROJECT_NAME
from .debug import console
from .utils import fopen
from .settings import Settings
from .task import Task
from .promise_progress import PromiseProgress
SIGNATURE = "aHR0cDovL3d3dy5zdWJsaW1lcmdlLmNvbS9idXkuaHRtbA"
VERIFY = "U3VibGltZXJnZS5zdWJsaW1lLWxpY2Vuc2U"
VERIFYU = "aHR0cHM6Ly9zdWJsaW1lcmdlLmNvbS9wYWNrYWdlcy5qc29u"
VERIFYV = "Uuc2UGZ3VibS5zdWJsltZXJnaY2VW1lLWxp"
EVALED = "U1VCTElNRVJHRTogRVZBTFVBVElPTiBDT1BZIChVTkxJQ0VOU0VEKQ"
SIGNATURE_1 = "VGhhbmtzIGZvciB0cnlpbmcgb3V0IFN1YmxpbWVyZ2UgMyENCg0KWW91ciBleGlzdGluZyBsaWNlbnNlIGhhcyBiZWVuIHN1Y2Nlc3NmdWx5IGltcG9ydGVkIGZyb20gU3VibGltZXJnZSBQcm8uIEEgbGljZW5zZSB1cGdyYWRlIHdpbGwgYmUgcmVxdWlyZWQgd2hlbiBTdWJsaW1lcmdlIDMgaXMgcmVsZWFzZWQgb2ZmaWNpYWxseS4NCg0KVW50aWwgdGhlbiwgcGxlYXNlIGVuam95IHRoZSBwcmV2aWV3IHZlcnNpb24gOik="
SIGNATURE_2 = "U3VibGltZXJnZQ0KDQpUaGFua3MgZm9yIHRyeWluZyBvdXQgU3VibGltZXJnZSENCg0KVGhpcyBpcyBhbiB1bnJlZ2lzdGVyZWQgZXZhbHVhdGlvbiB2ZXJzaW9uIGFuZCBhIGxpY2Vuc2UgbXVzdCBiZSBwdXJjaGFzZWQgZm9yIGNvbnRpbnVlZCB1c2UuDQoNCkJlIGZhaXIgYW5kIHN1cHBvcnQgZGV2ZWxvcG1lbnQuIEl0IGRvZXNuJ3QgY29zdCBtdWNoISA6KQ0KDQpXb3VsZCB5b3UgbGlrZSB0byBwdXJjaGFzZSBhIGxpY2Vuc2Ugbm93Pw=="
SIGNATURE_3 = "RW50ZXIgeW91ciBsaWNlbnNlIGtleTo="
SIGNATURE_4 = "U3VibGltZXJnZQ0KDQpMaWNlbnNlIGtleSBpcyBpbnZhbGlkIDoo"
SIGNATURE_5 = "U3VibGltZXJnZQ0KDQpSZWdpc3RyYXRpb24gc3VjY2Vzc2Z1bCEgVGhhbmsgeW91IDop"
SIGNATURE_6 = "U3VibGltZXJnZQ0KDQpMaWNlbnNlIGtleSBoYXMgYmVlbiByZW1vdmVkIHN1Y2Nlc3NmdWx5"
SIGNATURE_7 = "U3VibGltZXJnZQ0KDQpJdCBzZWVtcyB0aGF0IHVubGljZW5zZWQgY29weSBvZiBTdWJsaW1lcmdlIGlzIGluIHVzZSBmb3IgbW9yZSB0aGFuIDkwIGRheXMuIERldmVsb3BtZW50IGNvc3RzIG1lIGEgbG90IG9mIGVmZm9ydCBhbmQgbXkgc3BhcmUgdGltZSBzbyBwbGVhc2UgYmUgZmFpciBhbmQgbGVnYWwgYW5kIHB1cmNoYXNlIGEgbGljZW5zZS4NCg0KQm9yeXMgRm9yeXRhcnogLSBhdXRob3I="
SIGNATURE_8 = "U3VibGltZXJnZQoKQ291bGQgbm90IHZlcmlmeSBsaWNlbnNlIGtleSBhdCB0aGlzIHRpbWUuIFBsZWFzZSB0cnkgYWdhaW4gbGF0ZXIuCgpJZiB5b3UgYXJlIGJlaGluZCBhIHByb3h5LCBwbGVhc2UgdHJ5IGNvbmZpZ3VyaW5nIHByb3h5IHNldHRpbmdzLgpTZWUgYFByZWZlcmVuY2VzL1BhY2thZ2UgQ29udHJvbC9TdWJsaW1lcmdlL1NldHRpbmdzIC0gRGVmYXVsdGAgZm9yIG1vcmUgaW5mb3JtYXRpb24u"
SIGNATURE_9 = "U3VibGltZXJnZQ0KDQpLZXkgJXMgc2VlbXMgdG8gYmUgaW52YWxpZC4NCg0KSWYgeW91J3JlIGEgbGVnYWwgb3duZXIgb2YgdGhpcyBsaWNlbnNlIGtleSwgcGxlYXNlIGNvbnRhY3Qgc3VwcG9ydEBzdWJsaW1lcmdlLmNvbSBmb3IgYXNzaXN0YW5jZS4="
TYPE_SM_2 = "f"
TYPE_SM_3 = "sm3"
TYPE_EXP = "exp"
PROMPT_NO_MORE_OFTEN_THAN = 30
PROMPT_RUN_FREQUENCY = 4

def log(*args):
    if Settings.get("debug"):
        print("[Sublimerge %s]" % PROJECT_VERSION, *args)


def b64d(txt):
    return str(decode64(bytes(txt + "==", "utf-8")).decode("utf-8"))


def b64e(txt):
    return str(encode64(bytes(txt, "utf-8")).decode("utf-8")).replace("\n", "").replace("=", "")


def r_sh(text, os_fp):
    key = sha1(str(os_fp).encode("utf-8")).hexdigest()
    enc = []
    for i in range(len(text)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(text[i]) + ord(key_c)) % 256)
        enc.append(enc_c)

    return b64e("".join(enc))


def r_us(text, os_fp):
    key = sha1(str(os_fp).encode("utf-8")).hexdigest()
    dec = []
    text = b64d(text)
    for i in range(len(text)):
        key_c = key[i % len(key)]
        dec_c = chr((256 + ord(text[i]) - ord(key_c)) % 256)
        dec.append(dec_c)

    return "".join(dec)


class LInsp:
    types = [TYPE_SM_2, TYPE_SM_3, TYPE_EXP]
    fp = None
    last_prompt_time = 0
    run_number = 0

    @classmethod
    def r_init(self):
        path2 = self.r_f2()
        path3 = self.r_f3()
        if not os.path.exists(path3):
            if os.path.exists(path2) and self.r_il2(path2):
                sublime.message_dialog(b64d(SIGNATURE_1))
            else:
                self.r_iek()
        data = self.r_rl3()
        if data and self.r_vk_srv(data["key"]) is False:
            sublime.error_message(b64d(SIGNATURE_9) % data["key"])
            self.r_iek()

    @classmethod
    def r_f2(self):
        return os.path.join(sublime.packages_path(), "User", b64d(VERIFY))

    @classmethod
    def r_f3(self):
        tries = [
         os.path.realpath(os.path.join(sublime.packages_path(), "..", "Local")),
         os.path.join(sublime.packages_path(), PROJECT_NAME),
         sublime.installed_packages_path(),
         os.getenv("APPDATA") if sublime.platform() == "windows" else os.path.expanduser("~"),
         os.path.expanduser("~")]
        fname = ".id3" + self.os_fp()
        for p in tries:
            p = os.path.join(p, fname)
            if os.path.exists(p):
                return p

        for p in tries:
            if os.path.exists(p):
                p = os.path.join(p, fname)
                try:
                    with fopen(p, "w") as f:
                        f.write("")
                        f.close()
                        os.remove(p)
                    return p
                except Exception as e:
                    pass


    @classmethod
    def r_il2(self, path):
        with fopen(path, "r") as f:
            key = json.load(f)["key"]
            return self.r_ik(key)

    @classmethod
    def r_ik(self, key, expired=False, allow_expirable=False):
        try:
            t = self.r_vk(key)
            log("109", t)
            if not t or t == TYPE_EXP and not allow_expirable:
                return False
            expires = time.time() + 7776000 if t == TYPE_EXP else 0
            data = r_sh(b64e(json.dumps({"key": key, "expires": expires, "expired": expired})), self.os_fp())
            p = self.r_f3()
            f = fopen(p, "w")
            f.write(data)
            f.close()
            return True
        except Exception as e:
            p = os.path.dirname(self.r_f3())
            log("125", e, os.path.exists(p), os.access(p, os.W_OK))

        return False

    @classmethod
    def r_iek(self):
        expiring = self.r_mk(self.os_fp(), TYPE_EXP)
        expiring += "-" + self.r_mk(expiring, TYPE_EXP)
        self.r_ik(expiring, False, True)

    @classmethod
    def r_rl3(self):
        try:
            path = self.r_f3()
            with fopen(path, "r") as f:
                k = f.read()
                f.close()
                tries = [self.os_fp(), uuid.getnode(), uuid.getnode(), uuid.getnode()]
                for h in tries:
                    try:
                        data = b64d(r_us(k, h))
                        break
                    except:
                        pass

                return json.loads(data)
        except Exception as e:
            try:
                self.r_iek()
            except Exception as e:
                log("155", e)

            return False

    @classmethod
    def r_vk_srv(self, key):
        t = self.r_vk(key)
        if t == TYPE_EXP:
            return True
        if t in [TYPE_SM_2, TYPE_SM_3]:
            proxy = None
            try:
                s = sublime.load_settings("Package Control.sublime-settings")
                https_proxy = Settings.get("https_proxy") or (s.get("https_proxy") if s else None)
                https_proxy_u = Settings.get("proxy_username") or (s.get("proxy_username") if s else None)
                https_proxy_p = Settings.get("proxy_password") or (s.get("proxy_password") if s else None)
                credentials = "%s:%s@" % (https_proxy_u, https_proxy_p) if https_proxy_u and https_proxy_p else ""
                proxy = build_opener(ProxyHandler({"https": "https://%s%s" % (credentials, https_proxy)}))
            except Exception as e:
                print("Sublimerge: unable to set proxy: ", str(e))
            try:
                fp = self.os_fp()
                (urlstr, params) = (b64d(VERIFYU), ("t=%s" % b64e(",".join([t, sha1(key.encode("utf-8")).hexdigest(), fp, PROJECT_VERSION]))).encode("utf-8"))
                response = proxy.open(urlstr, params) if proxy else urlopen(urlstr, params)
                json_str = response.read().decode("utf-8")
                result = json.loads(json_str)
                if result["result"] is None:
                    return
                return result["result"] == sha1("/".join([t, PROJECT_VERSION, fp, VERIFYV]).encode("utf-8")).hexdigest()
            except Exception as e:
                print("Sublimerge: " + str(e))
            return
        return False

    @classmethod
    def r_ok(self):
        v, ex, expd = self.r_inf()
        return v and not ex

    @classmethod
    def r_inf(self):
        data = self.r_rl3()
        if not data:
            return (False, False, False)
        if "expired" not in data:
            data.update({"expired": False})
        t = self.r_vk(data["key"])
        expired = data["expires"] > 0 and (data["expired"] or data["expires"] < time.time())
        if not data["expired"] and expired:
            self.r_ik(data["key"], True, True)
        return (t in self.types, t == TYPE_EXP, expired)

    @classmethod
    def os_fp(self):
        if self.fp is None:
            sb = []
            try:
                arch = platform.architecture()
                sb.append(platform.node())
                sb.append(arch[0])
                sb.append(arch[1])
                sb.append(platform.machine())
                sb.append(platform.processor())
                sb.append(platform.system())
            except:
                pass

            sb.append(sublime.cache_path())
            sb.append(sublime.packages_path())
            sb.append(sublime.installed_packages_path())
            self.fp = sha1("#".join(sb).encode("utf-8")).hexdigest()
        return self.fp

    @classmethod
    def r_rem(self):
        self.run_number += 1
        v, ex, expd = self.r_inf()
        if ex and expd:
            self.r_op(SIGNATURE_7, False)
            return True
        if v and not ex or time.time() - self.last_prompt_time < PROMPT_NO_MORE_OFTEN_THAN:
            self.run_number = 0
            return False
        if self.run_number % PROMPT_RUN_FREQUENCY == 0:
            self.last_prompt_time = time.time()
            self.r_op(SIGNATURE_2, False)
            return True
        return False

    @classmethod
    def r_op(self, msg, force=False):
        if force or sublime.ok_cancel_dialog(b64d(msg)):
            s = "?v=" + PROJECT_VERSION + "&st=" + sublime.version()
            browser_open(b64d(SIGNATURE) + s)

    @classmethod
    def r_pfk(self):
        sublime.active_window().show_input_panel(b64d(SIGNATURE_3), "", self.r_rk, None, None)

    @classmethod
    def r_rk(self, k):
        k = k.strip()
        if not self.r_vk(k):
            sublime.error_message(b64d(SIGNATURE_4))
        else:

            def error_message(msg):
                sublime.set_timeout((lambda : sublime.error_message(msg)), 100)

            def message_dialog(msg):
                sublime.set_timeout((lambda : sublime.message_dialog(msg)), 100)

            def inner():
                r = self.r_vk_srv(k)
                if r is None:
                    error_message(b64d(SIGNATURE_8))
                    return
                if r is False:
                    error_message(b64d(SIGNATURE_9) % k)
                    return
                if self.r_ik(k):
                    message_dialog(b64d(SIGNATURE_5))
                else:
                    log("253")
                    error_message(b64d(SIGNATURE_4))

            loading = Task.spawn(inner)
            PromiseProgress(loading, "Please wait...")

    @classmethod
    def r_uk(self):
        if self.r_ok():
            os.remove(self.r_f3())
            sublime.message_dialog(b64d(SIGNATURE_6))

    @classmethod
    def r_mx(self, input):
        sha = sha1(input.encode("utf-8")).hexdigest()
        _len = len(sha)
        k = [" "] * _len
        i = 0
        for letter in sha:
            i += 1
            pos = ord(letter) * i % _len - i
            while pos >= _len or k[pos] != " ":
                pos = pos + 1
                if pos >= _len:
                    pos = 0
                    continue

            k[pos] = letter

        return k

    @classmethod
    def r_mk(self, input, type):
        letters = [
         'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 
         'j', 
         'k', 'l', 'm', 'n', 'p', 'q', 'r', 
         's', 
         't', 'u', 'v', 'w', 'x', 'y', 'z', 
         '1', 
         '2', '3', '4', '5', '6', '7', '8', 
         '9']
        k = ""
        txt = input + "@" + type
        arr = self.r_mx(input + "@" + type)
        i = 0
        while len(arr) > 0:
            pair = arr[0:2]
            arr = arr[2:]
            move = int("".join(pair), 16)
            k = k + letters[move % len(letters) - 1]
            i += 1
            if i % 4 == 0:
                k += "-"
                continue

        return k[0:-1].upper()

    @classmethod
    def r_vk(self, k):
        if re.match("^([A-Z0-9]{4}-){9}[A-Z0-9]{4}$", k):
            lines = [k[0:24], k[25:]]
            rev = [
             "1d40462e0bc18d029ab54ac5cb9796933bfe18b4",
             "c926ded08c9d6608c26cd9d82c6e78e52057f816",
             "aaa3b0039c7c286eb885de3c215c70859fb0a97e",
             "5e50888a865ea61cc24298dce0b6ca9d9b8d6e3f"]
            if str(sha1(k.encode("utf-8")).hexdigest()) in rev:
                log("326")
                return False
            for type in self.types:
                if self.r_mk(lines[0], type) == lines[1]:
                    log("331", type)
                    return type

            log("334")
        else:
            log("336")
        return False
