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
import re
import core.tree as tree
from core.acl import AccessData
import core.users as users
from core.translation import translate, getDefaultLanguage


class EditorNodeList:
    def __init__(self, nodes):
        self.nodeids = []
        self.nodeid2pos = {}
        for node in nodes:
            self.nodeids.append(node.id)
        i = 0
        for node in nodes:
            self.nodeid2pos[node.id] = i
            i = i + 1
    def getNext(self, nodeid):
        try:
            pos = self.nodeid2pos[nodeid] 
        except KeyError:
            return None
        if pos >= len(self.nodeids)-1:
            return None
        return self.nodeids[pos+1]
    def getPrevious(self, nodeid):
        try:
            pos = self.nodeid2pos[nodeid] 
        except KeyError:
            return None
        if pos <= 0:
            return None
        return self.nodeids[pos-1]
    def getPositionString(self,nodeid):
        try:
            pos = self.nodeid2pos[nodeid] 
        except KeyError:
            return ""
        return "%d / %d" % (pos+1, len(self.nodeids))

def getHomeDir(user):
    username = user.getName()
    userdir = None
    for c in tree.getRoot("home").getChildren():
        if (c.getAccess("read") or "").find("{user "+username+"}")>=0 and (c.getAccess("write") or "").find("{user "+username+"}")>=0:
            userdir = c
    if not userdir:
        userdir = tree.getRoot("home").addChild(tree.Node(name=translate("user_directory", getDefaultLanguage())+" ("+username+")", type="directory"))
        userdir.setAccess("read","{user "+username+"}")
        userdir.setAccess("write","{user "+username+"}")
    return userdir

def getUploadDir(user):
    userdir = getHomeDir(user)
    uploaddir = None
    for c in userdir.getChildren():
        if c.name == translate("user_upload", getDefaultLanguage()):
            uploaddir = c
    if not uploaddir:
        uploaddir = userdir.addChild(tree.Node(name=translate("user_upload", getDefaultLanguage()), type="directory"))
    return uploaddir

#
def getFaultyDir(user):
    userdir = getHomeDir(user)
    faultydir = None
    for c in userdir.getChildren():
        if c.name == translate("user_faulty", getDefaultLanguage()):
            faultydir = c
    if not faultydir:
        faultydir = userdir.addChild(tree.Node(name=translate("user_faulty", getDefaultLanguage()), type="directory"))
    return faultydir

#
def showdir(req,node):
    shownodelist(req,node.getChildren())


def shownodelist(req,nodes):
    req.session["nodelist"] = EditorNodeList(nodes)
    script_array = "allobjects = new Array();\n"
    nodelist = []

    for child in nodes:
        if child.type == "directory":
            continue
        script_array += "allobjects['"+child.id+"'] = 0;\n"
        nodelist.append(child)

    req.writeTAL("edit/edit_common.html", {"nodelist":nodelist, "script_array":script_array}, macro="show_nodelist")


def isUnFolded(unfoldedids, id):
    try:
        return unfoldedids[id]
    except:
        unfoldedids[id] = 0
        return 0

def writenode(req, node, unfoldedids, f, indent, key, access):
    if node.type != "directory" and node.type != "collection" and node.type != "root" and node.type != "home" and node.type != "collections" and node.type != "navigation":
        return
    if not access.hasReadAccess(node):
        return

    isunfolded = isUnFolded(unfoldedids, node.id)

    num = 0
    objnum = 0
    for c in node.getChildren():
        if c.type == "directory" or c.type == "collection":
            num += 1
        else:
            objnum += 1

    if num:
        if isunfolded:
            link = "edit_tree?tree_fold="+node.id;
            f(req,node,objnum,link,indent,type=1)
        else:
            link = "edit_tree?tree_unfold="+node.id;
            f(req,node,objnum,link,indent,type=2)
    else:
        link = ""
        f(req,node,objnum,link,indent,type=3)

    if isunfolded:
        for c in node.getChildren().sort():
            writenode(req, c, unfoldedids, f, indent+1, key, access)


def writetree(req, node, f, key="", openednodes=None, sessionkey="unfoldedids", omitroot=0):
    access = AccessData(req)

    try:
        unfoldedids = req.session[sessionkey]
        len(unfoldedids)
    except:
        req.session[sessionkey] = unfoldedids = {tree.getRoot().id : 1}

    if openednodes:
        # open all selected nodes and their parent nodes
        def o(u,n):
            u[n.id] = 1
            for n in n.getParents():
                o(u,n)
        for n in openednodes:
            o(unfoldedids, n)
        req.session[sessionkey] = unfoldedids

    try:
        unfold = req.params["tree_unfold"]
        unfoldedids[unfold] = 1
    except KeyError:
        pass
    
    try:
        fold = req.params["tree_fold"]
        unfoldedids[fold] = 0
    except KeyError:
        pass
   
    if omitroot:
        for c in node.getChildren().sort("name"):
            writenode(req, c, unfoldedids, f, 0, key, access)
    else:
        writenode(req, node, unfoldedids, f, 0, key, access)
