"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>

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

import core.tree as tree
import core.acl as acl
import core.users as users

from core.stats import buildStat, StatisticFile
from utils.utils import splitpath
from utils.date import format_date, now

def getPeriod(filename):
    filename = splitpath(filename)[-1]
    period = filename[:-4].split("_")[2]
    type = filename[:-4].split("_")[3]
    return period, type


def getContent(req, ids):
    if len(ids)>0:
        ids = ids[0]

    user = users.getUserFromRequest(req)
    node = tree.getNode(ids)
    access = acl.AccessData(req)
    
    if "statsaccess" in users.getHideMenusForUser(user) or  not access.hasWriteAccess(node):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if req.params.get("style", "")=="popup":
        getPopupWindow(req, ids)
        return ""

    node = tree.getNode(ids)
    statfiles = {}
    p = ""
    
    for file in node.getFiles():
        if file.getType()=="statistic":
            period, type = getPeriod(file.retrieveFile())
            if period>p:
                p = period
            
            if type not in statfiles.keys():
                statfiles[type] = {}
            
            if period not in statfiles[type].keys():
                statfiles[type][period] = []
                
            statfiles[type][period].append(file)

    v = {}
    v["id"] = ids
    v["files"] = statfiles
    v["current_period"] = req.params.get("select_period", "frontend_" + p)
    if len(statfiles)>0:
        v["current_file"] = StatisticFile(statfiles[v["current_period"].split("_")[0]][v["current_period"].split("_")[1]][0])
    else:
        v["current_file"] = StatisticFile(None)
    v["nodename"] = tree.getNode
    return req.getTAL("web/edit/modules/statsaccess.html", v, macro="edit_stats")

    
def getPopupWindow(req, ids):
    print req.params
    v = {}
    v["id"] = ids
    if "update" in req.params:
        v["action"] = "doupdate"
    
    elif req.params.get("action")=="do": # do action and refresh current month
        collection = tree.getNode(req.params.get("id"))
        collection.set("system.statsrun", "1")
        buildStat(collection, str(format_date(now(), "yyyy-mm")))
        req.writeTAL("web/edit/modules/statsaccess.html", {}, macro="edit_stats_result")
        collection.removeAttribute("system.statsrun")
        return
        
    else:
        print "show form step 1"
        v["action"] = "showform"
        v["statsrun"] = tree.getNode(ids).get("system.statsrun")
    req.writeTAL("web/edit/modules/statsaccess.html", v, macro="edit_stats_popup")
