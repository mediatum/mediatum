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
import core.athana as athana
import core.acl as acl
import core.tree as tree
import logging
import core.users as users
from core.acl import AccessData
from utils.utils import getCollection
from core.translation import t

log = logging.getLogger('edit')
utrace = logging.getLogger('usertracing')

def edit_sort(req, ids):
    print req.params
    user = users.getUserFromRequest(req)
    if "sort" in users.getHideMenusForUser(user):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return
    
    access = AccessData(req)
    node = tree.getNode(ids[0])
    runscript = False

    if not access.hasWriteAccess(node):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return

    up,down = -1,-1

    for key in req.params.keys():
        if key.startswith("up_"):
            up = int(key[3:-2])
            break
        if key.startswith("down_"):
            down = int(key[5:-2])
            break

    if "resort" in req.params:
        key = req.params["resort"].lower()
        i = 0
        for child in node.getChildren().sort(key, req.params.get("direction","up")):
            child.setOrderPos(i)
            i = i + 1
        runscript = True

    if up>=0 or down>=0:
        i = 0
        for child in node.getChildren().sort():
            try:
                if child.isContainer():
                    if i == up:
                        pos = i-1
                    elif i == up-1:
                        pos = up
                    elif i == down:
                        pos = i+1
                    elif i == down+1:
                        pos = down
                    else:
                        pos = i
                    child.setOrderPos(pos)
                    i = i + 1
            except:
                pass

        runscript = True
    nodelist = []

    for child in list(node.getChildren().sort()):
        try:
            if child.isContainer():
                nodelist.append(child)
        except:
            pass

    req.writeTAL("web/edit/edit_sort.html", {"node":node, "nodelist":nodelist, "runscript":runscript}, macro="edit_sort")
    return