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
import core.tree as tree
import os
import re

from utils.utils import *
from core.acl import AccessData
from web.frontend.frame import getNavigationFrame
from web.frontend.content import getContentArea,ContentNode

def display(req):
    content = getContentArea(req)
    content.feedback(req)

    navframe = getNavigationFrame(req)
    navframe.feedback(req)

    contentHTML = content.html(req)
    navframe.write(req, contentHTML)

def display_noframe(req):
    content = getContentArea(req)
    content.feedback(req)
    
    navframe = getNavigationFrame(req)
    navframe.feedback(req)

    contentHTML = content.html(req)
    if "raw" in req.params:
        req.write(contentHTML)
    else:
        navframe.write(req, contentHTML, show_navbar=0)

# needed for workflows:

PUBPATH = re.compile("/?(publish|pub)/(.*)$")
def publish(req):
    m = PUBPATH.match(req.path)

    node = tree.getRoot("workflows")
    if m: 
        for a in m.group(2).split("/"):
            if a: node = node.getChild(a)
    
    req.params["id"] = node.id

    content = getContentArea(req)
    content.content = ContentNode(node)
    
    return display_noframe(req)

def show_parent_node(req):
    id = req.params["id"]
    node = tree.getNode(id)
    parent = None
    for p in node.getParents():
        if p.type != "directory" and p.type != "collection":
            parent = p
    
    req.params["id"] = parent.id
    req.params["obj"] = node.id

    content = getContentArea(req)
    content.content = ContentNode(parent)

    return display_noframe(req)

