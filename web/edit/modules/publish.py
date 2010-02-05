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

import core.users as users
import core.tree as tree
import web.edit

from core.acl import AccessData
from core.translation import t, lang
from web.edit.edit_common import writetree, showdir, getHomeDir
from web.edit.edit import nodeIsChildOfNode
from edit import *#nodeIsChildOfNode
from utils.utils import isDirectory

def getInformation():
    return {"version":"1.0", "system":1}

def getContent(req, ids):
    user = users.getUserFromRequest(req)
    publishdir = tree.getNode(ids[0])
    access = AccessData(req)
    explicit = tree.getNodesByAttribute("writeaccess", user.getName())
    ret = ""

    if "dopublish" in req.params.keys():
        objlist = []
        for key in req.params.keys():
            if key.isdigit():
                objlist.append(key)
                src = tree.getNode(req.params.get("id"))
                
        for obj_id in objlist:
            obj = tree.getNode(obj_id)
            
            faultylist = []
            for mask in obj.getType().getMasks(type="edit"):
                if access.hasReadAccess(mask):
                    for f in mask.validateNodelist([obj]):
                        faultylist.append(f)

            if len(faultylist)>0:
                print "object not moved, faulty"
                continue
            
            for dest_id in req.params.get("destination", "").split(","):
                if dest_id=="":
                    print "dest empty"
                    continue
                
                dest = tree.getNode(dest_id)

                if dest != src and \
                   access.hasReadAccess(src) and \
                   access.hasWriteAccess(dest) and \
                   access.hasWriteAccess(obj) and \
                   isDirectory(dest):
                        if not nodeIsChildOfNode(dest,obj):
                            print "Move",obj.id,"from",src.id,"to",dest.id
                            dest.addChild(obj)
                            src.removeChild(obj)
                        else:
                            print "Couldn't copy",obj.id,"from",src.id,"to",dest.id,":",dest.id,"is child of",obj.id             
        ret += req.getTAL("web/edit/modules/publish.html", {"id":publishdir.id}, macro="reload")

    if req.params.get("style","")=="":
        # build normal window
        stddir = ""
        stdname = ""
        l = []
        for n in explicit:
            if str(getHomeDir(user).id)!=str(n):
                l.append(n)

        if len(l)==1:
            stddir = str(explicit[0])+","
            stdname = "- " + tree.getNode(explicit[0]).getName()
        ret += req.getTAL("web/edit/modules/publish.html", {"id":publishdir.id,"stddir":stddir, "stdname":stdname, "showdir":showdir(req, publishdir, publishwarn=0, markunpublished=1)}, macro="publish_form")
        return ret
        
    exparents = []
    for n in explicit:
        node = tree.getNode(n)
        if node not in exparents:
            for p in node.getParents():
                exparents.append(tree.getNode(p.id))

    parents = {}
    pnum = {}
    for id in ids:
        try:
            n = tree.getNode(id)
            for p in n.getParents():
                parents[p.id] = p
                pnum[p.id] = pnum.get(p.id,0)+1
        except tree.NoSuchNodeError:
            continue
            
            
    dest_names = "" 
    if req.params.get("unmark","")!="":
        req.params["mark"] = req.params.get("mark","").replace(req.params.get("unmark")+",","")
        
    for nid in req.params.get("mark","").split(","):
        try:
            n = tree.getNode(nid)
            dest_names += "- "+n.getName()+ "<br/>"
        except tree.NoSuchNodeError:
            continue
    
    

    def f(req,node,objnum,link,indent,type):
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
        v["writeaccess"] = access.hasWriteAccess(node)
        
        if node.id in req.params.get("mark","").split(","):
            v["icon"] = "/img/haken_s.gif"
            v["title"] = "edit_classes_disclass_title"
            v["link2"] = req.makeSelfLink({"mark":req.params.get("mark", ""), "unmark": node.id, "tree_unfold":"", "tree_fold":""})+"#node"+node.id
        else:
            v["icon"] = "/img/haken_n.gif"
            v["title"] = "edit_classes_class_title"
            v["link2"] = req.makeSelfLink({"mark":node.id+','+req.params.get("mark", ""), "unmark": "", "tree_unfold":"", "tree_fold":""})+"#node"+node.id
            
        return req.getTAL("web/edit/modules/publish.html", v, macro="build_tree")

    try: ntid = req.session["nodetreeid"]
    except KeyError: ntid = ""

    if ntid != ids[0]:
        req.session["nodetreeid"] = ids[0]
        try: del req.session["nodetree"]
        except: pass
        openednodes = parents.values()
    else:
        openednodes = []
    
    for n in exparents:
        openednodes.append(n)

    v = {}
    v["publishtree"] = writetree(req, tree.getRoot("collections"), f, "", openednodes=openednodes, sessionkey="nodetree", omitroot=0)
    v["mark"] = req.params.get('mark','')
    v["destnames"] = dest_names
    req.writeTAL("web/edit/modules/publish.html", v, macro="publish")
    return ""
    
    
