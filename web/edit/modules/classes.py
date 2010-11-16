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
import core.users as users
from web.edit.edit_common import writetree
from core.acl import AccessData


def getContent(req, ids):
    ret = ""
    user = users.getUserFromRequest(req)
    access = AccessData(req)
    nodes = []
    for id in ids:
        if not access.hasWriteAccess(tree.getNode(id)):
            return req.getTAL("web/edit/edit.html", {}, macro="access_error")
        nodes += [tree.getNode(id)]
    
    if "classes" in users.getHideMenusForUser(user):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    changed = 0
    try: 
        pid = req.params["unmark"]
        parent = tree.getNode(pid)
        for node in nodes:
            if not access.hasWriteAccess(node):
                return req.getTAL("web/edit/edit.html", {}, macro="access_error")

        changed = 1
        if not pid:
            raise KeyError
        if access.hasWriteAccess(parent):
            for node in nodes:
                try: parent.removeChild(node)
                except: pass
    except tree.NoSuchNodeError:
        pass
    except KeyError:
        pass
    
    try: 
        pid = req.params["mark"]
        parent = tree.getNode(pid)
        for node in nodes:
            if not access.hasWriteAccess(node):
                return req.getTAL("web/edit/edit.html", {}, macro="access_error")

        changed = 1
        if not pid:
            raise KeyError
        if access.hasWriteAccess(parent):
            for node in nodes:
                try: parent.removeChild(node) # protect against adding a child more than once
                except: pass
                try: parent.addChild(node)
                except: pass
    except tree.NoSuchNodeError:
        pass
    except KeyError:
        pass

    wrote_nomoreentries_msg = 0
    for node in nodes:
        if len(node.getParents()) == 0:
            faultydir = users.getFaultyDir(users.getUserFromRequest(req)).addChild(node)
            
            if not wrote_nomoreentries_msg:
                wrote_nomoreentries_msg = 1
                return req.getTAL("web/edit/modules/classes.html", {}, macro="entry_error")
                

    if changed:
        ret += '<script language="javascript">\nparent.reloadTree();\n</script>'

    parents = {}
    pnum = {}
    for id in ids:
        n = tree.getNode(id)
        for p in n.getParents():
            parents[p.id] = p
            pnum[p.id] = pnum.get(p.id,0)+1

    superparents = {}
    for node in parents.values():
        def addp(node):
            for p in node.getParents():
                superparents[p.id] = p
                addp(p)
        addp(node)

    
    def f(req, node, objnum, link, indent, type):
        indent *= 10
        
        nodename = node.name
        try: nodename = node.getLabel()
        except: 
            log.logException()
        
        if type==1:
            link = req.makeSelfLink({"unmark":"", "mark":"", "tree_unfold":"", "tree_fold":node.id})+"#node"+node.id
        elif type==2:
            link = req.makeSelfLink({"unmark":"", "mark":"", "tree_unfold":node.id, "tree_fold":""})+"#node"+node.id

        v = {}
        v["id"] = str(node.id)
        v["type"] = type
        v["link1"] = link
        v["indent"] = indent + 10
        v["nodename"] = nodename
        v["inqueue"] = node.id in superparents and type==2
        v["inparents"] = node.id in parents
        v["writeaccess"] = access.hasWriteAccess(node)
        
        if node.id in pnum and pnum[node.id]==len(nodes):
            v["icon"] = "/img/haken_s.gif"
            v["title"] = "edit_classes_disclass_title"
        else:
            v["icon"] = "/img/haken_g.gif"
            v["title"] = "edit_classes_class_title"
            
        v["link2"] = req.makeSelfLink({"unmark":node.id, "mark":"", "tree_unfold":"", "tree_fold":""})+"#node"+str(node.id) 
        v["link3"] = req.makeSelfLink({"mark":node.id, "unmark": "", "tree_unfold":"", "tree_fold":""})+"#node"+str(node.id)

        return req.getTAL("web/edit/modules/classes.html", v, macro="build_tree")

    try: ntid = req.session["nodetreeid"]
    except KeyError: ntid = ""

    if ntid != ids[0]:
        req.session["nodetreeid"] = ids[0]
        try: del req.session["nodetree"]
        except: pass
        openednodes = parents.values()
    else:
        openednodes = None

    ret += "<p>&nbsp;</p>"
    ret += writetree(req, tree.getRoot("home"), f, "", openednodes=openednodes, sessionkey="nodetree", omitroot=1)
    ret += writetree(req, tree.getRoot("collections"), f, "", openednodes=openednodes, sessionkey="nodetree", omitroot=0)
    return ret
