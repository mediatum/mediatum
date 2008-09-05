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
from utils.utils import compare_utf8,isDirectory,isCollection

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
        
        # re-sort home dirs alphabetically
        i = 0
        for child in tree.getRoot("home").getChildren().sort("name"):
            child.setOrderPos(i)
            i = i + 1
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

def getImportDir(user):
    userdir = getHomeDir(user)
    importdir = None
    for c in userdir.getChildren():
        if c.name == translate("user_import", getDefaultLanguage()):
            importdir = c
    if not importdir:
        importdir = userdir.addChild(tree.Node(name=translate("user_import", getDefaultLanguage()), type="directory"))
    return importdir

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


def getTrashDir(user):
    userdir = getHomeDir(user)
    trashdir = None
    for c in userdir.getChildren():
        if c.name == translate("user_trash", getDefaultLanguage()):
            trashdir = c
    if not trashdir:
        trashdir = userdir.addChild(tree.Node(name=translate("user_trash", getDefaultLanguage()), type="directory"))
    return trashdir

#
def showdir(req, node, publishwarn=1, markunpublished=0):
    shownodelist(req,node.getChildren(),publishwarn=publishwarn,markunpublished=markunpublished,dir=node)


def getAllSubDirs(node):
    #dirs = homedir.search("objtype=directory")
    dirs = []
    for c in node.getChildren():
        if c.type == "directory":
            dirs += [c] + getAllSubDirs(c)
    return dirs
            

def shownodelist(req, nodes, publishwarn=1, markunpublished=0, dir=None):
    req.session["nodelist"] = EditorNodeList(nodes)
    script_array = "allobjects = new Array();\n"
    nodelist = []
        
    user = users.getUserFromRequest(req)

    for child in nodes:
        if isDirectory(child) or isCollection(child):
            continue
        script_array += "allobjects['"+child.id+"'] = 0;\n"
        nodelist.append(child)

    chkjavascript = ""
    notpublished = {}
    if publishwarn or markunpublished:
        homedir = getHomeDir(user)
        homedirs = getAllSubDirs(homedir)
        if markunpublished:
            chkjavascript = """<script language="javascript">"""
        for node in nodes:
            ok = 0
            for p in node.getParents():
                if p not in homedirs:
                    ok = 1
            if not ok:
                if markunpublished:
                    chkjavascript += """allobjects['check%s'] = 1;
                                        document.getElementById('check%s').checked = true;
                                     """ % (node.id,node.id)

                notpublished[node] = node
        chkjavascript += """</script>"""
        # if all nodes are properly published, don't bother
        # to warn the user
        if not notpublished:
            publishwarn = 0

    unpublishedlink = None
    if publishwarn:
        user = users.getUserFromRequest(req)
        if dir:
            uploaddir = dir
        else:
            uploaddir = getUploadDir(user)
        unpublishedlink = "edit?tab=tab_publish&id="""+uploaddir.id;

    req.writeTAL("web/edit/edit_common.html", {"notpublished": notpublished, "chkjavascript": chkjavascript, "unpublishedlink": unpublishedlink, "nodelist":nodelist, "script_array":script_array}, macro="show_nodelist")


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
