from os import makedirs
from os.path import exists, join
import zipfile, sublime, codecs, zipimport
from .metadata import PROJECT_VERSION

def errmsg(msg, estr=None):
    sublime.set_timeout((lambda : sublime.error_message("%s%s%s" % (msg, "\n\n" if estr else "", estr))), 3000)


def unpack(tried=0):
    theme_path = join(sublime.packages_path(), "Theme - Default")
    if not exists(theme_path):
        try:
            makedirs(theme_path)
        except:
            sublime.error_message("Sublimerge\n\nCould not create directory: `%s`\n\nPlease create this directory manually and restart Sublime Text." % theme_path)
            return

    for pack_name in ["Sublimerge 3"]:
        pack_path = join(sublime.installed_packages_path(), "%s.sublime-package" % pack_name)
        unpack_path = join(sublime.packages_path(), pack_name)
        if exists(pack_path):
            if not exists(unpack_path):
                makedirs(unpack_path)
            version_path = join(unpack_path, "version")
            unpack = True
            if exists(version_path):
                try:
                    f = open(version_path, "r")
                    unpack = f.read() != PROJECT_VERSION
                    f.close()
                except LookupError:
                    f = codecs.open(version_path, "r", "utf-8")
                    unpack = f.read() != PROJECT_VERSION
                    f.close()

            if unpack:
                try:
                    resources = [
                     'icons/bline1.png', 
                     'icons/bline2.png', 
                     'icons/bline3.png', 
                     'icons/bline4.png', 
                     'icons/conflict.png', 
                     'icons/eline1.png', 
                     'icons/eline2.png', 
                     'icons/eline3.png', 
                     'icons/eline4.png', 
                     'icons/equal1.png', 
                     'icons/equal2.png', 
                     'icons/left1.png', 
                     'icons/left2.png', 
                     'icons/left3.png', 
                     'icons/left4.png', 
                     'icons/m_beline1.png', 
                     'icons/m_beline2.png', 
                     'icons/m_eline1.png', 
                     'icons/m_beline3.png', 
                     'icons/m_beline4.png', 
                     'icons/m_bline1.png', 
                     'icons/m_bline2.png', 
                     'icons/m_bline3.png', 
                     'icons/m_bline4.png', 
                     'icons/m_conflict.png', 
                     'icons/m_eline2.png', 
                     'icons/m_eline3.png', 
                     'icons/m_eline4.png', 
                     'icons/m_vline1.png', 
                     'icons/m_vline2.png', 
                     'icons/m_vline3.png', 
                     'icons/m_vline4.png', 
                     'icons/right1.png', 
                     'icons/right2.png', 
                     'icons/right3.png', 
                     'icons/right4.png', 
                     'icons/vline1.png', 
                     'icons/vline2.png', 
                     'icons/vline3.png', 
                     'icons/vline4.png', 
                     'Sublimerge 3.sublime-settings', 
                     'Sublimerge Macros.sublime-settings', 
                     'Default (Linux).sublime-keymap', 
                     'Default (Linux).sublime-mousemap', 
                     'Default (Windows).sublime-keymap', 
                     'Default (Windows).sublime-mousemap', 
                     'Default (OSX).sublime-keymap', 
                     'Default (OSX).sublime-mousemap', 
                     'EULA.txt', 
                     'syntax/Sublimerge.tmLanguage', 
                     'vendor/chardet/LICENSE.txt', 
                     'vendor/chardet/__init__.py', 
                     'vendor/chardet/big5freq.py', 
                     'vendor/chardet/big5prober.py', 
                     'vendor/chardet/chardetect.py', 
                     'vendor/chardet/chardistribution.py', 
                     'vendor/chardet/charsetgroupprober.py', 
                     'vendor/chardet/charsetprober.py', 
                     'vendor/chardet/codingstatemachine.py', 
                     'vendor/chardet/compat.py', 
                     'vendor/chardet/constants.py', 
                     'vendor/chardet/cp949prober.py', 
                     'vendor/chardet/escprober.py', 
                     'vendor/chardet/escsm.py', 
                     'vendor/chardet/eucjpprober.py', 
                     'vendor/chardet/euckrfreq.py', 
                     'vendor/chardet/euckrprober.py', 
                     'vendor/chardet/euctwfreq.py', 
                     'vendor/chardet/euctwprober.py', 
                     'vendor/chardet/gb2312freq.py', 
                     'vendor/chardet/gb2312prober.py', 
                     'vendor/chardet/hebrewprober.py', 
                     'vendor/chardet/jisfreq.py', 
                     'vendor/chardet/jpcntx.py', 
                     'vendor/chardet/langbulgarianmodel.py', 
                     'vendor/chardet/langcyrillicmodel.py', 
                     'vendor/chardet/langgreekmodel.py', 
                     'vendor/chardet/langhebrewmodel.py', 
                     'vendor/chardet/langhungarianmodel.py', 
                     'vendor/chardet/langthaimodel.py', 
                     'vendor/chardet/latin1prober.py', 
                     'vendor/chardet/mbcharsetprober.py', 
                     'vendor/chardet/mbcsgroupprober.py', 
                     'vendor/chardet/mbcssm.py', 
                     'vendor/chardet/sbcharsetprober.py', 
                     'vendor/chardet/sbcsgroupprober.py', 
                     'vendor/chardet/sjisprober.py', 
                     'vendor/chardet/universaldetector.py', 
                     'vendor/chardet/utf8prober.py']
                    z = zipfile.ZipFile(pack_path, "r")
                    for resource in resources:
                        z.extract(resource, unpack_path)

                    z.close()
                    try:
                        f = open(version_path, "w")
                        f.write(PROJECT_VERSION)
                        f.close()
                    except LookupError:
                        f = codecs.open(version_path, "w", "utf-8")
                        f.write(PROJECT_VERSION)
                        f.close()

                except Exception as e:
                    estr = str(e)
                    if estr.find("zlib") != -1:
                        errmsg("There is a problem with zlib in your Sublime Text Python's distribution. You may try to re-install Sublime Text.", estr)
                    elif estr.find("denied") != -1:
                        errmsg("Unable to unpack resources. Please correct access rights and restart Sublime Text.", estr)
                    else:
                        raise

            continue

    for pack_name in ["Sublimerge 3"]:
        unpack_path = join(sublime.packages_path(), pack_name)
        if exists(unpack_path):
            return unpack_path
