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
import time
import core.users as users
import core.tree as tree
import core.config as config

from utils.utils import esc,getCollection
from core.translation import t, lang
from core.acl import AccessData
import logging

log = logging.getLogger('frontend')

def isUnFolded(unfoldedids, id):
    try:
        return unfoldedids[id]
    except:
        unfoldedids[id] = 0
        return 0

def writenode(req, node, unfoldedids, f, indent, accessdata):
    isunfolded = isUnFolded(unfoldedids, node.id)
    
    num = 0
    for c in node.getChildren():
        if c.can_open():
            num = num + 1

    type = 3
    if num:
        type -= 1
        if isunfolded:
            type -= 1

    css = ""
    if req.params.get("dir",1)==node.id:
        css = "current"

    
    if not accessdata.hasReadAccess(node):
        return ""
    if not (node.type == "directory" or node.type == "collection" or node.type == "root"):
        return ""

    ret ='<li class="'+css+'"><div class="nav_div" style="margin-left: '+str(indent+35)+'px">'+f(req, node, type)+'</div></li>'

    if isunfolded:
        for c in node.getChildren().sort():
            ret += writenode(req, c, unfoldedids, f, indent+20, accessdata)
    return ret

def writetree2(req, node, f, content, unfoldedids=None):
    
    user = users.getUserFromRequest(req)
    
    def openParents(unfoldedids, node):
        for p in node.getParents():
            unfoldedids[p.id] = 1
            openParents(unfoldedids, p)

    if unfoldedids is None:
        try:
            unfoldedids = req.session["unfoldedids"]
            len(unfoldedids)
        except:
            print "error1"
            req.session["unfoldedids"] = unfoldedids = {}
    else:
        u = unfoldedids.copy()
        unfoldedids = {}
        for k,v in u.items():
            if v:
                openParents(unfoldedids, tree.getNode(k))
    try:
        unfold = req.params["unfold"]
        unfoldedids[unfold] = 1
        openParents(unfoldedids, tree.getNode(unfold))
    except:
        print "error2"
        pass
    
    try:
        fold = req.params["fold"]
        unfoldedids[fold] = 0
        openParents(unfoldedids, tree.getNode(fold))
    except:
        print "error3"
        pass
        
    accessdata = AccessData(req)
   
    for c in node.getChildren().sort():
        content += writenode(req, c, unfoldedids, f, 10, accessdata)

    return content

def writetree(req, mynode, currentdir, content):
    
    def makeLink(req,node,type):
        count = 0
        for n_t,num in node.getAllOccurences().items():
            if n_t.getTypeName() != "directory":
                count += num

        items = " (" + str(count) + ")"        
        link = 'node?id='+node.id+'&dir='+node.id

        if type == 1:
            return '<div class="nav_img"><a href="'+link+'&fold='+node.id+'" title="'+t(lang(req),"fold")+'" class="type1">_</a></div><div class="nav_text"><a href="'+link+'&fold='+node.id+'" class="type1"> '+node.getLabel()+" "+items+'</a></div>'
        elif type == 2:
            return '<div class="nav_img"><a href="'+link+'&unfold='+node.id+'" title="'+t(lang(req),"unfold")+'" class="type2">_</a></div><div class="nav_text"><a href="'+link+'&unfold='+node.id+'" class="type2"> '+node.getLabel()+" "+items+'</a></div>'
        else:
            return '<div class="nav_img"><img src="/img/box_3.gif"/></div><div class="nav_text"><a href="'+link+'">' + node.getLabel() + " " + items+ '</a></div>'

    return writetree2(req, mynode, makeLink, content, {currentdir.id: 1})

def cleartree():
    None

def browsingtree(req):
    #try:
    content=""
    print req.params.get("collection",1)
    mynode = tree.getNode(req.params.get("collection",1))
    currentdir = tree.getNode(req.params["dir"])
    content=writetree(req, mynode, currentdir, content)
    return content
    #except:
    #    print "error4"
    #    return ""
