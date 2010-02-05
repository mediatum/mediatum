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


def getContent(req,ids):
    user = users.getUserFromRequest(req)
    access = AccessData(req)
    node = tree.getNode(ids[0])
    
    if "sortfiles" in users.getHideMenusForUser(user) or not access.hasWriteAccess(node):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    c = getCollection(node)
    
    if "globalsort" in req.params:
        c.set("sortfield", req.params["globalsort"])
    collection_sortfield = c.get("sortfield")

    class SortChoice:
        def __init__(self, label, value):
            self.label = label
            self.value = value

    sortfields = [SortChoice(t(req,"off"),"")]
    for ntype,num in c.getAllOccurences(AccessData(req)).items():
        if ntype.getSortFields():
            for sortfield in ntype.getSortFields():
                sortfields += [SortChoice(sortfield.getLabel(), sortfield.getName())]
                sortfields += [SortChoice(sortfield.getLabel()+t(req,"descending"), "-"+sortfield.getName())]
            break

    return req.getTAL("web/edit/modules/sortfiles.html", {"node":node, "collection_sortfield":collection_sortfield,
                                         "sortchoices":sortfields, "name":c.getName()}, macro="edit_sortfiles")
