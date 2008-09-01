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
import edit

from core.acl import AccessData
from core.translation import t, lang
from edit_common import writetree, showdir, getHomeDir
from edit import *#nodeIsChildOfNode


def edit_publish(req, ids):
    print "req:", req.params
    user = users.getUserFromRequest(req)
    publishdir = tree.getNode(ids[0])
    access = AccessData(req)
    
    explicit = tree.getNodesByAttribute("writeaccess", user.getName())

    if "dopublish" in req.params.keys():
        objlist = []
        for key in req.params.keys():
            if key.isdigit():
                objlist.append(key)

        src = tree.getNode(req.params.get("id"))
        for obj_id in objlist:
            obj = tree.getNode(obj_id)
            
            for dest_id in req.params.get("destination", "").split(","):
                if dest_id=="":
                    continue
                
                dest = tree.getNode(dest_id)

                if dest != src and \
                   access.hasReadAccess(src) and \
                   access.hasWriteAccess(dest) and \
                   access.hasWriteAccess(obj) and \
                   edit.isDirectory(dest):
                    if not edit.nodeIsChildOfNode(dest,obj):
                        print "Move",obj.id,"from",src.id,"to",dest.id
                        dest.addChild(obj)
                        src.removeChild(obj)
                    else:
                        print "Couldn't copy",obj.id,"from",src.id,"to",dest.id,":",dest.id,"is child of",obj.id             
        req.write("<script>parent.reloadTree("+publishdir.id+");</script>")

    
    if req.params.get("style","")=="":
        # build normal window
        stddir = ""
        stdname=""
        l = []
        for n in explicit:
            if str(getHomeDir(user).id)!=str(n):
                l.append(n)

        if len(l)==1:
            stddir = str(explicit[0])+","
            stdname = "- " + tree.getNode(explicit[0]).getName()

        req.write('<form action="/edit/edit_content?id='+publishdir.id+'&tab=tab_publish" method="post" style="margin:5px" name="publishform">')
        req.writeTAL("web/edit/edit_publish.html", {"id":publishdir.id,"stddir":stddir, "stdname":stdname}, macro="publish_form")
        showdir(req, publishdir, publishwarn=0, markunpublished=1)
        req.write("</form>")
        return

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
        indent += 10
        req.write('<a name="node%s"></a>' % node.id)
        req.write('<div class="line">')
        req.write(' <div class="name" style="padding-left: '+str(indent)+'px">')
        title = 'title="'+t(lang(req),"edit_classes_class_title")+'"'
        

        if type == 1:
            l = req.makeSelfLink({"unmark":"", "mark":req.params.get("mark"), "tree_unfold":"", "tree_fold":node.id})
            req.write('<a title="'+t(lang(req), "edit_classes_close_title")+'" href="%s"><img src="/img/edit_box1.gif" border="0"></a>' % (l+"#node"+node.id))
            title = 'title="'+t(lang(req),"edit_classes_disclass_title")+'"'
        elif type == 2:
            l = req.makeSelfLink({"unmark":"", "mark":req.params.get("mark"), "tree_unfold":node.id, "tree_fold":""})
            req.write('<a title="'+t(lang(req), "edit_classes_open_title")+'" href="%s"><img src="/img/edit_box2.gif" border="0"></a>' % (l+"#node"+node.id))
        elif type == 3:
            req.write('<img src="/img/edit_box3.gif" border="0">')

        nodename = node.name
        try: nodename = node.getLabel()
        except: 
            log.logException()

        if access.hasWriteAccess(node):
            req.write('&nbsp;<b>'+nodename+'</b>')
            if node.id in req.params.get("mark","").split(","):
                req.write('&nbsp;<a '+title+' href="%s#node%s"><img border="0" src="/img/haken_s.gif"></a>' % (req.makeSelfLink({"mark":req.params.get("mark", ""), "unmark": node.id, "tree_unfold":"", "tree_fold":""}),node.id))
            else:
                req.write('&nbsp;<a '+title+' href="%s#node%s"><img border="0" src="/img/haken_n.gif"></a>' % (req.makeSelfLink({"mark":node.id+','+req.params.get("mark", ""), "unmark": "", "tree_unfold":"", "tree_fold":""}),node.id))

        else:
            req.write('&nbsp;'+nodename)
            
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
        openednodes = []
    
    for n in exparents:
        openednodes.append(n)

    req.write("""    
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">
            <html>
            <head>
              <META http-equiv="Content-Type" content="text/html; charset=UTF-8">
              <meta content="text/html;charset=UTF-8" http-equiv="content-type">
              <link rel="stylesheet" href="/css/editor.css">
              <link rel="stylesheet" href="/css/edit_style.css">
              <script type="text/javascript" src="/js/editor.js"></script>
              <script type="text/javascript" src="/js/admin.js"></script>
              <script type="text/javascript" src="/js/mediatum.js"></script>
              <script>
                function closewindow(){
                    var v1 = document.getElementById("destination");
                    var v2 = document.getElementById("destnames");
                    opener.returnvalues(v1.value, v2.value);
                    self.close();
                }
                
                function cancel(){
                    opener.publishform.destination.value = "";
                    self.close();
                }
              </script>
            </head><body>
            <form>
            <h3>"""+t(lang(req),"edit_publish_popupheader")+"""</h3>
    """)

    writetree(req, tree.getRoot("collections"), f, "", openednodes=openednodes, sessionkey="nodetree", omitroot=0)
    req.write('<input type="hidden" name="destination" id="destination" value="'+req.params.get('mark','')+'" />')
    req.write('<input type="hidden" name="destnames" id="destnames" value="'+dest_names+'"/>')
    req.write("""
            <p align="center"><button type="button" onclick="closewindow()" style="width:100px">"""+t(lang(req),"edit_publish_ok")+"""</button>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<button type="button" onclick="cancel()" style="width:100px">"""+t(lang(req),"edit_publish_cancel")+"""</button></p>
        </form>
        </body>
    </html>   
    """)
    
    
    
