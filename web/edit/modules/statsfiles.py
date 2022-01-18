# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging

import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
from utils.date import format_date
from core.users import user_from_session as _user_from_session
from core import httpstatus
from core import Node
from core import db

q = db.query
logg = logging.getLogger(__name__)


class StatType:

    def __init__(self, name):
        self.name = name
        self.data = {}
        self.digit = {}

    def addItem(self, schema, digit=0):
        if not schema in self.data.keys():
            self.data[schema] = 0
            self.digit[schema] = 0

        self.data[schema] += 1
        if digit == 1:
            self.digit[schema] += 1

    def getName(self):
        return self.name

    def getTypes(self):
        backitems = [[v[0], v[1], self.digit[v[0]]] for v in self.data.items()]
        backitems.sort(lambda x, y: cmp(y[1], x[1]))
        return backitems

    def getMax(self):
        if len(self.data) > 0:
            return int(self.getTypes()[0][1])
        return 0

    def getSum(self):
        sum = 0
        for item in self.data:
            sum += int(self.data[item])
        return sum

    def getSumDigit(self):
        sum = 0
        for item in self.digit:
            sum += int(self.digit[item])
        return sum


class StatTypes:

    def __init__(self, datastring=""):
        self.data = []
        if datastring != "":  # convert string to objects
            datastring += ";"
            for type in datastring.split(");"):
                if len(type) > 1:
                    data = type.split("(")
                    t = StatType(data[0])
                    for item in data[1].split(";"):
                        item = item.split("=")
                        t.data[item[0]] = int(item[1].split("|")[0])
                        t.digit[item[0]] = int(item[1].split("|")[1])
                    self.data.append(t)

        self.data.sort(lambda x, y: cmp(y.getMax(), x.getMax()))

    def addItem(self, type, schema, digit=0):
        d = None
        for datatype in self.data:
            if datatype.getName() == type:
                d = datatype
                break
        if not d:  # type not found, create new
            d = StatType(type)
            self.data.append(d)
        d.addItem(schema, digit)

    def getTypes(self):
        return [item.getName() for item in self.data]

    def __str__(self):
        ret = ""
        for t in self.data:
            ret += t.getName() + "("
            for i in t.getTypes():
                ret += i[0] + "=" + ustr(i[1]) + "|" + ustr(i[2]) + ";"
            if ret[-1] == ";":
                ret = ret[:-1]
            ret += ");"
        return ret[:-1]

    def getMax(self):
        max = 0
        for datatype in self.data:
            if datatype.getMax() > max:
                max = datatype.getSum()
        return max

    def getSum(self):
        sum = 0
        for datatype in self.data:
            sum += datatype.getMax()
        return sum


def getContent(req, ids):
    if len(ids) > 0:
        ids = ids[0]

    user = _user_from_session()
    node = q(Node).get(ids)

    if "statsfiles" in user.hidden_edit_functions or not node.has_write_access():
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    if "update_stat" in req.params.keys():  # reset stored statistics data
        logg.info("user %s requests update of of system.statscontent for node %s (%s, %s)", user.login_name, node.id, node.name, node.type)
        node.removeAttribute("system.statscontent")
        node.removeAttribute("system.statsdate")

    # content
    if req.params.get("style", "") == "popup":
        statstring = node.get("system.statscontent")

        if statstring == "":  # load stats from objects/renew stat
            data = StatTypes()
            for n in node.all_children:
                found_dig = 0 or len(
                    [file for file in n.files if file.filetype in["image", "document", "video"]])
                data.addItem(n.type, n.schema, found_dig)

            node.set("system.statscontent", unicode(data))
            node.set("system.statsdate", unicode(format_date()))
            statstring = unicode(data)

        v = {}
        v["data"] = StatTypes(statstring)

        v["stand"] = node.get("system.statsdate")

        req.response.set_data(_tal.processTAL(v, file="web/edit/modules/statsfiles.html", macro="edit_stats_popup", request=req))
        return ""

    return _tal.processTAL(
            dict(id=ids, csrf=_core_csrfform.get_token()),
            file="web/edit/modules/statsfiles.html",
            macro="edit_stats",
            request=req,
        )
