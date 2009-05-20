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
from edit_common import writetree, getFaultyDir
from core.translation import t, lang
from core.acl import AccessData


def edit_classes(req, ids):
    user = users.getUserFromRequest(req)
    access = AccessData(req)
    nodes = []
    for id in ids:
        if not access.hasWriteAccess(tree.getNode(id)):
            req.writeTAL("web/edit/edit.html", {}, macro="access_error")
            return "error"
        nodes += [tree.getNode(id)]
    
    if "classes" in users.getHideMenusForUser(user):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return

    changed = 0
    try: 
        pid = req.params["unmark"]
        parent = tree.getNode(pid)
        for node in nodes:
            if not access.hasWriteAccess(node):
                req.writeTAL("web/edit/edit.html", {}, macro="access_error")
                return
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
                req.writeTAL("web/edit/edit.html", {}, macro="access_error")
                return

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

    wrote_nomoreentries_msg=0
    for node in nodes:
        if len(node.getParents()) == 0:
            faultydir = getFaultyDir(users.getUserFromRequest(req))
            faultydir.addChild(node)
            if not wrote_nomoreentries_msg:
                req.writeTAL("web/edit/edit_classes.html", {"lang":lang(req)}, macro="entry_error")
                wrote_nomoreentries_msg=1

    if changed:
        req.write("""
        <script language="javascript">
            parent.reloadTree();
        </script>
        """)

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

    
    def f(req,node,objnum,link,indent,type):
        indent *= 10
        indent += 10
        req.write('<a name="node%s"></a>' % node.id)
        req.write('<div class="line">')
        req.write(' <div class="name" style="padding-left: '+str(indent)+'px">')
        title = 'title="'+t(lang(req),"edit_classes_class_title")+'"'
        if type == 1:
            l = req.makeSelfLink({"unmark":"", "mark":"", "tree_unfold":"", "tree_fold":node.id})
            req.write('<a title="'+t(lang(req), "edit_classes_close_title")+'" href="%s"><img src="/img/edit_box1.gif" border="0"></a>' % (l+"#node"+node.id))
            title = 'title="'+t(lang(req),"edit_classes_disclass_title")+'"'
        elif type == 2:
            l = req.makeSelfLink({"unmark":"", "mark":"", "tree_unfold":node.id, "tree_fold":""})
            req.write('<a title="'+t(lang(req), "edit_classes_open_title")+'" href="%s"><img src="/img/edit_box2.gif" border="0"></a>' % (l+"#node"+node.id))
        elif type == 3:
            req.write('<img src="/img/edit_box3.gif" border="0">')

        nodename = node.name
        try: nodename = node.getLabel()
        except: 
            log.logException()

        if node.id in parents:
            if node.id in superparents and type==2:
                req.write('<font color="#3030ef">&nbsp;<b>'+nodename+'</b></font>')
            else:
                req.write('<font color="#3030ef">&nbsp;'+nodename+'</font>')
            if access.hasWriteAccess(node):
                if pnum[node.id] == len(nodes):
                    img = "haken_s"
                else:
                    img = "haken_g"
                req.write('&nbsp;<a '+title+' href="%s#node%s"><img border="0"src="/img/%s.gif"></a>' % (req.makeSelfLink({"unmark":node.id, "mark":"", "tree_unfold":"", "tree_fold":""}),node.id,img))
            else:
                req.write('&nbsp;<img border="0"src="/img/haken.gif">')

        else:
            if node.id in superparents and type==2:
                req.write('<font color="#3030ef">&nbsp;<b>'+nodename+'</b></font>')
            else:
                req.write('&nbsp;'+nodename)
            if access.hasWriteAccess(node):
                req.write('&nbsp;<a '+title+' href="%s#node%s"><img border="0" src="/img/haken_n.gif"></a>' % (req.makeSelfLink({"mark":node.id, "unmark": "", "tree_unfold":"", "tree_fold":""}),node.id))

        req.write(" </div>")
        req.write("</div>")

    try: ntid = req.session["nodetreeid"]
    except KeyError: ntid = ""

    if ntid != ids[0]:
        req.session["nodetreeid"] = ids[0]
        try: del req.session["nodetree"]
        except: pass
        openednodes = parents.values()
    else:
        openednodes = None

    req.write("<p>&nbsp;</p>")

    writetree(req, tree.getRoot("home"), f, "", openednodes=openednodes, sessionkey="nodetree", omitroot=1)
    writetree(req, tree.getRoot("collections"), f, "", openednodes=openednodes, sessionkey="nodetree", omitroot=0)
