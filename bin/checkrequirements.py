"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2011 Werner Neudenberger <neudenberger@ub.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# 'Usage: python bin/checkrequirements.py'
#   parameters (optional):
#       -c [path_to_mediatum_cfg] (default is ./mediatum.cfg)
#       -d for details

import sys
import os
import platform
import getopt
import textwrap
from subprocess import Popen, PIPE
from functools import reduce

res_dict = {}
failures = {}
CFG_FILE = 'mediatum.cfg'
DETAILS = 0


def out(msg, appendix='', blockwidth=98, borderchar='+', title=''):
    out_str = textwrap.fill(msg, blockwidth) + appendix
    print title.center(100, borderchar)
    for line in out_str.split('\n'):
        print "%s %s %s" % (borderchar, line.center(96), borderchar)
    print borderchar * (100)


try:
    opts, args = getopt.getopt(sys.argv[1:], "c:d")
except getopt.GetoptError as e:
    fn = __file__.replace('\\', '/').split('/')[-1]
    print '\nError:', e
    print 'Usage: python bin/' + fn + ' [-c path_to_mediatum_cfg (default is ./mediatum.cfg) -d for details]'
    sys.exit(2)

for o, a in opts:
    if o == '-c':  # config file
        CFG_FILE = a
    if o == '-d':  # details
        DETAILS = 1

print "Checking installation requirements for mediatum:"
print " Python version is %s.%s.%s" % (sys.version_info[:3])
print " Platform: %s (%s)\n %s" % (platform.system(), platform.architecture()[0], platform.platform())

if not sys.version_info[0:2] == (2, 7):
    fail_msg = "A recent Python version 2.7.x is needed"
    print "\n---> !!! FAIL: " + fail_msg
    failures["0"] = [('FAIL', fail_msg)]


def check_python_module(names):
    res = [0] * len(names)
    for name in names:
        try:
            __import__(name)
            res[names.index(name)] = 1
        except:
            pass
    return res


def check_fts3_enabled_sqlite(names):
    res = [0, 0, 0]
    try:
        import sqlite3 as sqlite
        msg = "module '%s' found, " % names[0]
        res[0] = 1
        con = sqlite.connect(":memory:")
        con.execute("create virtual table t using fts3(a, b)")
        res[2] = 1
    except:
        try:
            from pysqlite2 import dbapi2 as sqlite
            res[1] = 1
            con = sqlite.connect(":memory:")
            con.execute("create virtual table t using fts3(a, b)")
            res[2] = 1
        except:
            pass

    return res


# ["name", "short description", ["command", "args"], "fail_comment"]
external_tools_descrs = [
    ["mysql-server", "mysql-server: relational database server present on current host", ["mysql", "-V"], "RESTRICTION"],
    ["pdfinfo", "Xpdf: 'pdfinfo' to extract meta information of pdf files", ["pdfinfo", "-v"], "FAIL"],
    ["pdftotext", "Xpdf: 'pdftotext' to extract pdf-text", ["pdftotext", "-v"], "FAIL"],
    ["convert", "ImageMagick: 'convert' to extract pdf-text", ["convert", "-version"], "FAIL"],
    ["ffmpeg", "ffmpeg: to extract video thumbnails (flv), required for video support", ["ffmpeg", "-version"], "RESTRICTION"],
    ["graphviz", "graphviz: required for static workflow diagrams", ["dot", "-V"], "RESTRICTION"],
]

# [["module name(s)",], "name of alternative module", "short description", "fail_comment"]
python_module_descrs = [
    [["MySQLdb"], "MySQLdb: mysql connector (required for mysql usage)", check_python_module, "RESTRICTION"],
    [["sqlite3", "pysqlite2", "fts3"],
     "sqlite3/pysqlite2: sqlite3 connector with fts3 (required for searchmodule)", check_fts3_enabled_sqlite, "FAIL"],
    [["Image"], "PIL: python imaging library (pil)", check_python_module, "FAIL"],
    [["reportlab"], "reportlab: pdf reporting library (module 'reportlab')", check_python_module, "FAIL"],
    [["simplejson", "json"], "json/simplejson: json encoder and decoder ", check_python_module, "FAIL"],
    [["ldap"], "ldap: LDAP client API (required for LDAP authentication)", check_python_module, "RESTRICTION"],
    [["PyZ3950"], "PyZ3950: Z39.50 server for python", check_python_module, "RESTRICTION"],
    [["pymarc"], "pymarc: marc formatter for python", check_python_module, "RESTRICTION"],
    [["Levenshtein"], "python-Levenshtein: computing string distances and similarities", check_python_module, "RESTRICTION"],
    [["pyPdf"], "pyPdf: PDF toolkit", check_python_module, "RESTRICTION"],
    [["requests"], "requests: HTTP request module, required for DOI import", check_python_module, "FAIL"],
    [["pydot"], "pydot: python graphviz module, required for static workflow diagrams", check_python_module, "RESTRICTION"],
]


def step1():
    failures["1"] = []
    print "\nStep 1:\nChecking external tools\n" + '-' * 100
    for [name, descr, cmd, fail_comment] in external_tools_descrs:
        res_dict[name] = 0
        print '- ' + descr,
        try:
            Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()
            msg = "OK"
            res_dict[name] = 1
        except:
            msg = fail_comment
            failures["1"].append((fail_comment, name + ' not found.'))
        print " " * (97 - len(msg) - len(descr)) + msg

    if len(failures["1"]) > 0:
        out("Not all external tools are present, %s error(s) or restriction(s) found" % (len(failures)), borderchar='*')
    else:
        out("All external tools are present.", borderchar='+')


def step2():
    failures["2"] = []
    print "\nStep 2:\nChecking Python modules\n" + '-' * 100

    for [name, descr, func, fail_comment] in python_module_descrs:
        print '- ' + descr,
        mods = func(name)
        if sum(mods) >= len(mods) - 1 and sum(mods) > 0:
            msg = "OK"
            res_dict[name[0]] = 1
        else:
            msg = fail_comment
            failures["2"].append((fail_comment, name[0] + ' module not found.'))
        print " " * (97 - len(msg) - len(descr)) + msg

    if len(failures["2"]) > 0:
        out("Not all software requirements are met.", borderchar='*')
    else:
        out("All software requirements seem to be met.", borderchar='+')


def step3():
    failures["3"] = []
    print "\nStep 3:\nChecking configuration file '%s/%s'\n" % (os.getcwd(), CFG_FILE) + "-" * 100

    sys.path.append('core')  # import core/config.py without loading core/__init__.py (which whould start the web server)
    import config

    try:
        config.settings = config._read_ini_file(os.getcwd(), CFG_FILE)
    except IOError as e:
        msg = "Fatal error reading configuration file '%s': %s\n"
        msg += 'The default name of the configuration file is \'mediatum.cfg\'. '
        msg += "You can override this using the -c <path_to_config_file> option for this script."
        msg += "Look at mediatum.cfg.template for an explaining template."

        out(msg % (CFG_FILE, ustr(e)), borderchar='*', title=' Configuration: ')
        sys.exit()

    def check_setting(key, default):
        value = config.get(key)
        comment = value
        if not value:
            comment = 'no value set'
            value = ''
            if default:
                value = default
                comment += " (using default: '%s')" % default
        return value, comment

    def step3a():  # check [paths]
        import getpass
        failures["3a"] = []
        print "a) Checking [paths] settings: (Remark: mediatum user needs read and write access to this paths)"

        for pn in ['datadir', 'searchstore', 'tempdir']:
            access_descr = ""
            p = config.get('paths.' + pn)
            if p is None:
                p = ustr("")
            if not p:
                msg = "- path.%s: path value has not been set" % (pn)
                print msg + " " * (96 - len(msg)) + "FAIL"
                failures["3a"].append(('FAIL', 'missing value %s' % pn))
                continue
            else:
                if not os.path.isdir(p):
                    msg = "- path.%s: '%s' is not a directory" % (pn, p)
                    print msg + " " * (96 - len(msg)) + "FAIL"
                    failures["3a"].append(('FAIL', 'missing path %s' % p))
                    continue

                access_descr = "- path.%s: '%s' read/write access for user '%s'" % (pn, p, getpass.getuser())
                if os.access(p, os.R_OK) and os.access(p, os.W_OK):
                    access_descr += " " * (98 - len(access_descr)) + "OK"
                else:
                    access_descr += " " * (96 - len(access_descr)) + "FAIL"
                    failures["3a"].append(('FAIL', 'missing rights for %s' % pn))

                print access_descr

    def step3b():  # check [database]
        print '\nb) Checking [database] settings:'
        failures["3b"] = []
        dbtype, dbtype_comment = check_setting("database.type", "mysql")

        if dbtype in ['sqlite', 'sqllite']:  # use sqlite as database
            msg = "- database.type=%s: sqlite will be used, no further [database] settings required" % (dbtype)
            print msg + " " * (98 - len(msg)) + "OK"

            if 'sqlite3' not in res_dict.keys() or res_dict['sqlite3'] == 0:  # no sqlite connector present -> exit
                out("sqlite configured, but no connector (sqlite3 or pysqlite2) present. System won't be functional.", borderchar='*')
                sys.exit(2)
        else:  # use mysql as database
            if not dbtype:
                msg = '- database.type not set: mysql (default) will be used'
            else:
                msg = "- database.type=%s: mysql (default) will be used" % (dbtype)

            print msg + " " * (98 - len(msg)) + "OK"

            if 'MySQLdb' not in res_dict.keys() or res_dict['MySQLdb'] == 0:  # no mysql connector present -> exit
                failures["3b"].append(('FAIL', 'config.database(mysql)'))
                out("mysql configured, but no connector (MySQLdb) present. System won't be functional.", borderchar='*')
                sys.exit(2)

            dbhost, dbhost_comment = check_setting("database.dbhost", "localhost")
            dbport, dbport_comment = check_setting("database.dbport", "3306")
            database, db_comment = check_setting("database.db", "mediatum")
            user, user_comment = check_setting("database.user", "mediatumadmin")
            passwd, passwd_comment = check_setting("database.passwd", None)
            if passwd == '':
                passwd_comment = "- no password - (default)"
            else:
                passwd_comment = "**** (password used)"

            msg = "   settings:\n    database.host:   %s\n" % (dbhost_comment)
            msg += "    database.port:   %s\n    database.db:     %s\n" % (dbport_comment, db_comment)
            msg += "    database.user:   %s\n    database.passwd: %s" % (user_comment, passwd_comment)
            print msg

            import MySQLdb
            import _mysql_exceptions

            try:
                dbport = int(dbport)
                if dbport < 0:
                    raise ValueError()
            except ValueError as e:
                out("Fatal Error: database.port=%s is not a positive integer" % (ustr(dbport)), borderchar='*')
                sys.exit(1)

            try:
                msg = "- checking mysql network parameters (host:port=%s:%d)" % (dbhost, dbport)
                db = MySQLdb.connect(host=dbhost, port=dbport)
                print msg + " " * (98 - len(msg)) + "OK"

            except _mysql_exceptions.OperationalError as e:
                error_number, error_msg = e[0], e[-1]
                if error_number == 1045:  # server responds, but denies access
                    print msg + " " * (98 - len(msg)) + "OK"
                else:
                    msg += ", wrong settings"
                    print msg + " " * (96 - len(msg)) + "FAIL"
                    failures["3b"].append(('FAIL', 'wrong mysql network settings.'))
                    return

            try:
                msg = "- checking mysql credentials on %s:%d database: %s  user: %s" % (dbhost, dbport, database, user)
                db = MySQLdb.connect(host=dbhost, port=dbport, user=user, passwd=passwd, db=database)
                print msg + " " * (98 - len(msg)) + "OK"

            except _mysql_exceptions.OperationalError as e:
                print msg + " " * (96 - len(msg)) + "FAIL"
                failures["3b"].append(('FAIL', "wrong mysql credential settings." + ustr(e)))

    def step3c():
        failures["3c"] = []
        print '\nc) Checking [ldap] activation:'
        ldap_activate, ldap_activate_comment = check_setting("ldap.activate", "false")
        msg = "- ldap.activate=%s" % (ldap_activate_comment)
        if not ldap_activate.lower() == 'true':
            print "ldap.activate is not 'true': default 'false' will be used"

        if ldap_activate.lower() == 'true' and res_dict['ldap'] == 0:
            msg += ": ldap connector (module ldap) not present"
            print msg + " " * (96 - len(msg)) + "FAIL"
            failures["3c"].append(('FAIL', 'ldap connector (module ldap) not present'))

        if ldap_activate.lower() == 'true' and res_dict['ldap'] == 1:
            msg += ": ldap connector (module ldap) present"
            print msg + " " * (98 - len(msg)) + "OK"

    step3a()
    step3b()
    step3c()

    if (len(failures["3a"]) + len(failures["3b"]) + len(failures["3c"])) > 0:
        out("Errors in configuration file found, system won't be functional.", borderchar='*')
    else:
        out("All required configuration parameters are correct.", borderchar='+')


def result():
    print ""

    if sum([len(failures[x]) for x in failures]) == 0:
        out('All checked requirements met.\nThis installation should work.', title=' Summary ', borderchar='+')

    else:
        l = reduce(lambda x, y: x + y, [failures[x][0] for x in failures if len(failures[x]) > 0])
        if 'FAIL' in l:
            out('Some FAIL in installation (see above)\nSystem won\'t be functional.', title=' Summary ', borderchar='*')

        elif 'RESTRICTION' in l:
            out('Some RESTRICTION in installation (see above)\nSystem will run, but some features will not be available.',
                title=' Summary: ', borderchar='*')

        if DETAILS == 1:
            print "\nRequirement check result protocol:\n"
            steps = sorted(failures.keys())

            for step in steps:
                if len(failures[step]) > 0:
                    print "Step " + step + ":"
                    for item in failures[step]:
                        print " -", item[0] + ":" + " " * (15 - len(item[0])) + item[1]


# run check
step1()
step2()
step3()
result()
