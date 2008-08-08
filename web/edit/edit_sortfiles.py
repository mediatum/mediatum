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
import core.users as users
import logging
from core.acl import AccessData
from utils.utils import getCollection
from core.translation import t

log = logging.getLogger('edit')
utrace = logging.getLogger('usertracing')


def edit_sortfiles(req,ids):
    user = users.getUserFromRequest(req)
    if "sortfiles" in users.getHideMenusForUser(user):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return
    access = AccessData(req)
    node = tree.getNode(ids[0])
    if not access.hasWriteAccess(node):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return

    c = getCollection(node)
    
    if "globalsort" in req.params:
        c.set("sortfield", req.params["globalsort"])
    collection_sortfield = c.get("sortfield")

    sortchoices = []
    class SortChoice:
        def __init__(self, label, value):
            self.label = label
            self.value = value
        
    req.write("<h2>"+c.getName()+"</h2>")

    sortfields = [SortChoice(t(req,"off"),"")]
    for ntype,num in c.getAllOccurences(AccessData(req)).items():
        #req.write(ntype.getName() +" " +str(num)+"<br/>")
        if ntype.getSortFields():
            for sortfield in ntype.getSortFields():
                sortfields += [SortChoice(sortfield.getLabel(), sortfield.getName())]
                sortfields += [SortChoice(sortfield.getLabel()+t(req,"descending"), "-"+sortfield.getName())]
            break

    req.writeTAL("web/edit/edit_sort.html", {"node":node, "collection_sortfield":collection_sortfield,
                                         "sortchoices":sortfields}, macro="edit_autosort")
