# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import core.translation as _core_translation
import core.users as users
import core.acl as acl
import re


def getRuleUsers(s, userlist):
    while s[0] == "{"and s[-1] == "}":
        s = s[1:-1]

    def extractUser(s, userlist):
        while s[0] == "("and s[-1] == ")":
            s = s[1:-1]

        if s.startswith("user "):
            s = s[5:]

        for utype in userlist.keys():
            if users.getExternalUser(s, utype):
                return (utype, s)
        return ("", s)

    def parse(s, l):
        pattern_user = re.compile("\\b[oO][rR]\\b")
        m = pattern_user.search(s)
        if m:
            sub = s[:m.start()].strip()
            l.append(extractUser(sub, userlist))
            parse(s[m.end():].strip(), l)
        else:
            l.append(extractUser(s, userlist))
        return l
    ret = parse(s, [])

    return ret


def makeUserList(req, name, rights, readonlyrights, overload=0, type=""):
    val_left = ""
    val_right = ""
    rulelist = acl.getRuleList()
    userlist = {}
    userlist['intern'] = users.loadUsersFromDB()

    for usertype in list(users.getExternalUsers()):
        userlist[usertype.getName()] = users.getExternalUsers(usertype.getName())

    rightsmap = {}
    rorightsmap = {}
    for r in rights:
        for u in getRuleUsers(r, userlist):
            if _core_translation.translate(u[0], _core_translation.lang(req)) != "":
                rightsmap[_core_translation.translate(u[0], "{}: {}".format(_core_translation.lang(req)), u[1])] = None
            else:
                rightsmap[u[1]] = None

    rrights = []
    for r in readonlyrights:
        if r[0] == "{":
            for part in getRuleUsers(r, userlist):
                rrights.append("{}: {}".format(
                        _core_translation.translate(part[0], _core_translation.lang(req)),
                        part[1],
                    ))
        else:
            rrights.append(r)

    readonlyrights = rrights

    if not (len(rightsmap) > 0 and overload):
        # inherited standard rules
        for rule in rulelist:
            if rule.getName() in readonlyrights:
                val_left += """<optgroup label="%s"></optgroup>""" % (rule.getDescription())
                rorightsmap[rule.getName()] = 1

        # inherited implicit rules
        for rule in readonlyrights:
            if rule not in rorightsmap:
                val_left += """<optgroup label="%s"></optgroup>""" % (rule)

    # node-level implicit rules
    for r in rightsmap.keys():
        if not rightsmap[r] and r not in rorightsmap:
            val_left += """<option value="%s">%s</option>""" % (r, r)

    for usertype in userlist.keys():
        susers = list(userlist[usertype])
        susers.sort(lambda x, y: cmp(x.getName().lower(), y.getName().lower()))

        for user in susers:
            val = u"{}: {}".format(_core_translation.translate(usertype, _core_translation.lang(req)), user.getName())
            if val not in rightsmap and user.getName() not in rorightsmap and val not in readonlyrights:
                val_right += '<option value="{0}">{0}</option>'.format(val)

    return {"name": name, "val_left": val_left, "val_right": val_right, "type": type}
