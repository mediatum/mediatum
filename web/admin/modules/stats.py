"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

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
import os
import core.config as config

from core.db.database import getConnection
from utils.utils import get_filesize, format_filesize
from core.tree import getRoot
from utils.date import format_date


def getInformation():
    return {"version": "1.0", "required": 1}


def getTotalSize(conn):
    files = conn.runQuery("select filename from nodefile")
    size = 0
    rootpath = config.get("paths.datadir")
    for file in files:
        size += get_filesize(os.path.join(rootpath, file[0]))
    return size


def getOverviewData(req):
    conn = getConnection()
    num = {}
    num['nodes'] = str(conn.runQuery("select count(*) from node")[0][0])
    num['metadata'] = str(conn.runQuery("select count(*) from nodeattribute")[0][0])
    num['files'] = str(conn.runQuery("select count(*) from nodefile where type='document' or type='image'")[0][0])
    num['size'] = format_filesize(getTotalSize(conn))
    return num


def validate(req, op):
    return view(req)


def view(req):
    page = req.params.get("page", "")
    gotopage = req.params.get("gotopage", "")
    root = getRoot()

    v = {}
    v["gotopage"] = gotopage

    def format_num(nums):
        num = ""
        for k in nums:
            num += k + ":" + str(nums[k]) + ";"
        return num

    if gotopage == "overview" and req.params.get("changes") == "overview":
        for key in req.params.keys():
            if key == "overview_reset":
                root.set("admin.stats.num", format_num(getOverviewData(req)))
                root.set("admin.stats.updatetime", str(format_date()))
                break

    if page == "overview":

        num = root.get("admin.stats.num")
        if num == "":
            root.set("admin.stats.num", format_num(getOverviewData(req)))
            root.set("admin.stats.updatetime", str(format_date()))

        n = {}
        for items in num[:-1].split(";"):
            n[items.split(":")[0]] = items.split(":")[1]

        v['num'] = n
        v['date'] = root.get("admin.stats.updatetime")

        return req.getTAL("web/admin/modules/stats.html", v, macro="view_overview")
    elif page == "type":
        return req.getTAL("web/admin/modules/stats.html", v, macro="view_type")
    elif page == "size":
        return req.getTAL("web/admin/modules/stats.html", v, macro="view_size")
    else:

        return req.getTAL("web/admin/modules/stats.html", v, macro="view")
