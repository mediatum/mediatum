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
import core.tree as tree
#from utils import *
#from date import *
from core.acl import AccessData

def edit_license(req, ids):
    node = tree.getNode(ids[0])
    req.writeTAL("edit/edit_license.html", {"node":node}, macro="edit_license_info")

def objlist(req):
    node = tree.getNode(req.params["id"])
    
    if node.id == tree.getRoot().id:
        return

    access = AccessData(req)
    if not access.hasWriteAccess(node):
        return

    req.writeTAL("edit/edit_license.html", {"node":node}, macro="edit_license")
