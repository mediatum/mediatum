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
from core.acl import AccessData
from core.db import database

import core.users as users
import core.tree as tree
import logging

from utils.date import format_date, parse_date, now
from utils.utils import formatException
from core.translation import lang, t

db = database.getConnection()

def getContent(req, ids):
    ret = ""
    user = users.getUserFromRequest(req)
    
    if "metadata" in users.getHideMenusForUser(user):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    access = AccessData(req)
    faultydir = users.getFaultyDir(user)
    metatypes = []
    nodes = []
    masklist = []
    
    for id in ids:
        node = tree.getNode(id)
        if not access.hasWriteAccess(node):
            return req.getTAL("web/edit/edit.html", {}, macro="access_error")

        schema = node.getSchema()
        if schema not in metatypes:
            metatypes.append(schema)
        if len(nodes)==0 or nodes[0].getSchema()==schema:
            nodes += [node]

    idstr = ",".join(ids)

    for m in node.getType().getMasks(type="edit"):
        if access.hasReadAccess(m):
            masklist.append(m)
            
    if hasattr(node, "metaFields"):
                
        class SystemMask:
            def __init__(self, name, description, fields):
                self.name,self.description,self.fields = name,description,fields
            def getName(self):
                return self.name
            def getDescription(self):
                return self.description
            def getDefaultMask(self):
                return False
            def metaFields(self, lang=None):
                return self.fields
            def i_am_not_a_mask():
                pass
        masklist = [SystemMask("settings", t(req, "settings"), node.metaFields(lang(req)))] + masklist

    default = None
    for m in masklist:
        if m.getDefaultMask():
            default = m
            break
    if not default and len(masklist):
        default = masklist[0]

    maskname = req.params.get("mask", node.get("edit.lastmask") or "editmask")
    if maskname=="":
        maskname = default.getName()

    mask = None
    for m in masklist:
        if maskname==m.getName():
            mask = m
            break

    if not mask and default:
        mask = default
        maskname = default.getName()

    for n in nodes:
        n.set("edit.lastmask", maskname)

    if not mask:
        return req.getTAL("web/edit/modules/metadata.html", {}, macro="no_mask")

    action = req.params.get('action', '').strip()
    
    if action=='restore':
        vid = req.params.get('vid', '0')
        node = nodes[0].getActiveVersion()
        if (vid!='0' and vid!=node.id):
            n = tree.getNode(vid)
            # Not active version
            if n.next_nid!='0':
                    
                next = tree.getNode(n.next_nid)
                if next.prev_nid!='0':
                    next.removeChild(tree.getNode(next.prev_nid))
                next.setPrevID(n.prev_nid)

                if n.prev_nid!='0':
                    prev = tree.getNode(n.prev_nid)
                    prev.setNextID(n.next_nid)
                    n.removeChild(prev)
                    next.addChild(prev)
                node.setNextID(n.id)

                n.setPrevID(node.id)
                n.setNextID('0')

                for pid in db.getParents(node.id):
                    parentNode = tree.getNode(pid)
                    parentNode.addChild(n)
                    parentNode.removeChild(node)
                n.addChild(node)
                
                nodes = [n]
                ids = [n.id]
                return req.getTAL("web/edit/modules/metadata.html", {'url':'?id='+n.id+'&tab=metadata', 'pid':None}, macro="redirect")

    if action=='delete':
        vid = req.params.get('vid', '0')
        if (vid!='0'):
            node = nodes[0].getActiveVersion()
            n = tree.getNode(vid)
            
            if (vid!=node.id):
                n.set("deleted", "true")
                for pid in db.getParents(n.id):
                    parentNode = tree.getNode(pid)
                    parentNode.removeChild(n)
                for cid in db.getChildren(n.id):
                    n.removeChild(tree.getNode(cid))
                if n.next_nid!='0' and n.prev_nid!='0':
                    _next = tree.getNode(n.next_nid)
                    _next.addChild(tree.getNode(n.prev_nid))
                    
                if n.next_nid!='0':
                    _next = tree.getNode(n.next_nid)
                    if n.prev_nid!='0':
                        _next.setPrevID(n.prev_nid)

                if n.prev_nid!='0':
                    _prev = tree.getNode(n.prev_nid)
                    if n.next_nid!='0':
                        _prev.setNextID(n.next_nid)
            else:
                pids = db.getParents(n.id)
                
                # Active version
                prev = None
                if n.prev_nid!='0':
                    prev = tree.getNode(n.prev_nid)
                    while prev.prev_nid!=None and prev.prev_nid!='0' and prev.get("deleted")=="true":
                        prev = tree.getNode(prev.prev_nid)
                
                if prev!=None and prev.get("deleted")!="true":
                    prev.setNextID('0')
                    for pid in pids:
                        parentNode = tree.getNode(pid)
                        parentNode.addChild(prev)
                    nodes = [prev]
                    ids = [prev.id]
                    n.set("deleted", "true")
                    for pid in pids:
                        parentNode = tree.getNode(pid)
                        parentNode.removeChild(n)

                    for cid in db.getChildren(n.id):
                        n.removeChild(tree.getNode(cid))

                    if n.next_nid!='0' and n.prev_nid!='0':
                        _next = tree.getNode(n.next_nid)
                        _next.addChild(tree.getNode(n.prev_nid))

                    return req.getTAL("web/edit/modules/metadata.html", {'url':'?id='+prev.id+'&tab=metadata', 'pid':None}, macro="redirect")
                else:
                    # Version 0
                    # Move node to trash
                    trashdir = users.getTrashDir(user)
                    trashdir.addChild(n)
                    for pid in pids:
                        parentNode = tree.getNode(pid)
                        parentNode.removeChild(n)

                    return req.getTAL("web/edit/modules/metadata.html", {'url':'?id='+pids[0]+'&tab=content', 'pid':pids[0]}, macro="redirect")

    if "edit_metadata" in req.params:
        # check and save items
        userdir = users.getHomeDir(users.getUserFromRequest(req))

        for node in nodes:
            if not access.hasWriteAccess(node) or node.id == userdir.id:
                return req.getTAL("web/edit/edit.html", {}, macro="access_error")

        logging.getLogger('usertracing').info(access.user.name + " change metadata "+idstr)

        if not hasattr(mask,"i_am_not_a_mask"):
            errorlist = []
            if (req.params.get('generate_new_version')):
                # Create new node version
                _ids = []
                _nodes = []
                for node in nodes:
                    if (req.params.get('version_comment', '').strip()==''
                        or req.params.get('version_comment', '').strip()=='&nbsp;'):
                        errorlist.append(node.id)
                        _nodes.append(node)
                        _ids.append(node.id)
                    else:
                        n = node.createNewVersion(user)
                        n.set("system.version.comment", '('+t(req, "document_new_version_comment")+')\n'+req.params.get('version_comment', ''))
                        
                        _nodes.append(n)
                        _ids.append(n.id)

                ids = _ids
                idstr = ",".join(ids)
                nodes = _nodes
                nodes = mask.updateNode(nodes, req)
                errorlist += mask.validateNodelist(nodes)
                if len(errorlist)==0:
                    ret += req.getTAL("web/edit/modules/metadata.html", {'url':'?id='+nodes[0].id+'&tab=metadata', 'pid':None}, macro="redirect")
            else:
                nodes = mask.updateNode(nodes, req)
                errorlist += mask.validateNodelist(nodes)
        else:
            for field in mask.metaFields():
                field_name = field.getName()
                if field_name=='nodename':
                    field_name = getDefaultLanguage()+'__nodename' 
                value = req.params.get(field_name, None)
                if value is not None:
                    for node in nodes:
                        node.set(field.getName(), value)
                else:
                    node.set(field.getName(), "")
            errorlist = []

        if len(errorlist)>0 and "save" in req.params:
            ret+= '<p class="error">'+t(lang(req), "fieldsmissing") + '<br>'+t(lang(req), 'saved_in_inconsistent_data')+'</p>'

        for node in nodes:
            node.set("updateuser", user.getName())
            if node.get('updatetime')<str(now()):
                node.set("updatetime", str(format_date()))

        for node in nodes:
            if node.id in errorlist:
                faultydir.addChild(node)
                node.setAttribute("faulty", "true")
            else:
                faultydir.removeChild(node)
                node.removeAttribute("faulty")

    if "edit_metadata" in req.params or node.get("faulty")=="true":
        if not hasattr(mask, "i_am_not_a_mask"):
            req.params["errorlist"] = mask.validate(nodes)

    update_date = []
    if len(nodes)==1:
        for node in nodes:
            if node.get("updatetime"):
                try:
                    date = parse_date(node.get("updatetime"),"%Y-%m-%dT%H:%M:%S")
                    datestr = format_date(date, format='%d.%m.%Y %H:%M:%S')
                except:
                    datestr = node.get("updatetime")
                update_date.append([node.get("updateuser"),datestr])

    creation_date = []
    if len(nodes)==1:
        for node in nodes:
            if node.get("creationtime"):
                try:
                    date = parse_date(node.get("creationtime"),"%Y-%m-%dT%H:%M:%S")
                    datestr = format_date(date, format='%d.%m.%Y %H:%M:%S')
                except:
                    datestr = node.get("creationtime")
                creation_date.append([node.get("creator"), datestr])

    node_versions = nodes[0].getVersionList()
    
    data = {}
    data["user"] = user
    data["access"] = access
    data["metatypes"] = metatypes
    data["idstr"] = idstr
    data["node"] = nodes[0]
    data["versions"] = node_versions
    data["masklist"] = masklist
    data["maskname"] = maskname
    data["creation_date"] = creation_date
    data["update_date"] = update_date
    if not hasattr(mask,"i_am_not_a_mask"):
        data["maskform"] = mask.getFormHTML(nodes, req)
        data["fields"] = None
    else:
        data["maskform"] = None
        data["fields"] = mask.metaFields()
    ret += req.getTAL("web/edit/modules/metadata.html", data, macro="edit_metadata")
    return ret
    
