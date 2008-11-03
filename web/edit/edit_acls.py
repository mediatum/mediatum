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
from web.common.acl_web import makeList
from web.common.accessuser_web import makeUserList
from edit_common import getHomeDir

from utils.utils import removeEmptyStrings

log = logging.getLogger('edit')
acl_types = ["read", "write", "data"]


def show_acl_editor(req, ids):
    
    idstr=""
    for id in ids:
        if idstr:
            idstr+=","
        idstr+=id

    access = acl.AccessData(req)

    if "save" in req.params:
        #save acl level
        if req.params.get("type")=="acl":
        
            userdir = getHomeDir(users.getUserFromRequest(req))
            logging.getLogger('usertracing').info(access.user.name + " change access "+idstr)
            for type in acl_types:
                rights = req.params.get("left"+type, "").replace(";",",")
                for id in ids:
                    node = tree.getNode(id)
                    error = 0
                    if access.hasWriteAccess(node) and userdir.id != node.id:
                        node.setAccess(type, rights)
                    else:
                        error = 1
                    if error:
                        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
                        return
                        
        #save userlevel
        elif req.params.get("type")=="user":
            userdir = getHomeDir(users.getUserFromRequest(req))
            logging.getLogger('usertracing').info(access.user.name + " change access "+idstr)
            for type in acl_types:
                for id in ids:
                    node = tree.getNode(id)
                    error = 0
                    if access.hasWriteAccess(node) and userdir.id != node.id:
                        r = []
                        r_acls = []
                        if req.params.get("leftuser"+type,"")!="":
                            for right in req.params.get("leftuser"+type, "").split(";"):
                                if len(right.split(": "))==2:
                                    r.append("(user " + right.split(": ")[1]+ ")")
                                else:
                                    r_acls.append(right)
                                    print "sonst", right
                                if len(r)>0:
                                    rstr = "{"+" OR ".join(r)+"}"
                                else:
                                    rstr = req.params.get("leftuser"+type,"")

                                if len(rstr)>0:
                                    rstr += "," 
                                    
                                for x in r_acls:
                                    rstr += x+","
                                    
                                rstr = rstr[:-1]
                        else:
                            rstr = ""
                        node.setAccess(type, rstr)
                    else:
                        error = 1
                    if error:
                        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
                        return

    runsubmit = "\nfunction runsubmit(){\n"
    for type in acl_types:
        runsubmit +="\tmark(document.myform.left"+type+");\n"
        runsubmit +="\tmark(document.myform.leftuser"+type+");\n"
    runsubmit +="\tdocument.myform.submit();\n}\n"
    
    retacl = ""
    retuser = ""
    
    for type in acl_types:
        overload = 0
        if type in ("read","data"):
            overload = 1
        
        s = None
        parent_rights = {}
        for id in ids:
            node = tree.getNode(id)
            r = node.getAccess(type)
            if r is None:
                r = ""
            log.debug(node.name+" "+type+" "+r)
            if not s or r == s:
                s = r
            else:
                s = ""
            def addNode(node):
                for p in node.getParents():
                    aclright = p.getAccess(type)
                    for right in removeEmptyStrings((aclright or "").split(",")):
                        parent_rights[right] = None
                    if aclright and overload:
                        return
                    else:
                        addNode(p)
            addNode(node)

        rights = removeEmptyStrings(s.split(","))

        retacl += req.getTAL("web/edit/edit_acls.html", makeList(req, type, rights, parent_rights.keys(), overload, type=type), macro="edit_acls_selectbox")
        retuser += req.getTAL("web/edit/edit_acls.html", makeUserList(req, type, rights, parent_rights.keys(), overload, type=type), macro="edit_acls_userselectbox")

    if not access.getUser().isAdmin():
        retuser = retacl

    req.writeTAL("web/edit/edit_acls.html", {"runsubmit":runsubmit, "idstr":idstr, "contentacl":retacl, "contentuser":retuser, "adminuser":access.getUser().isAdmin()}, macro="edit_acls")
    return athana.HTTP_OK

def edit_acls(req, ids):
    return show_acl_editor(req, ids)
