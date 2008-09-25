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
import sys
import os
import re
import time
import urllib
import core.tree as tree
import core.config as config
import core.users as users
import core.usergroups as usergroups
import core.translation
import core.athana as athana
import utils.log
from core.acl import AccessData
from utils.utils import Link,isCollection, Menu

from edit_common import *
from edit_acls import edit_acls
from edit_metadata import edit_metadata
from edit_classes import edit_classes
from edit_files import edit_files
from edit_upload import edit_upload, upload_help
from edit_import  import edit_import
from edit_search import edit_search
from edit_sort import edit_sort
from edit_subfolder import edit_subfolder
from edit_sortfiles import edit_sortfiles
from edit_searchmask import edit_searchmask
from edit_editor import edit_editor
from edit_workflow import edit_workflow
from edit_license import edit_license
from edit_lza import edit_lza
from edit_logo import edit_logo
from edit_publish import edit_publish
from core.translation import lang, t

from edit_common import EditorNodeList


def frameset(req):
    id = req.params.get("id", tree.getRoot().id)
    tab = req.params.get("tab", None)

    user = users.getUserFromRequest(req)

    uploaddir = getUploadDir(user)
    importdir = getImportDir(user)
    faultydir = getFaultyDir(user)
    trashdir = getTrashDir(user)

    currentdir = tree.getNode(id)
    script="""
            var idselection = "";
            var action = "";

            function setFolderAction(_action)
            {
                if(_action == 'newfolder') {
                    openWindow("edit_action?newfolder=Neuer%20Ordner&src="+tree.getFolder(),300,200);
                } else if(_action == 'newcollection') {
                    openWindow("edit_action?newcollection=Neue%20Kollektion&src="+tree.getFolder(),300,200);
                } else if(_action == 'sortsubfolders') {
                    this.location.href = "edit?tab=tab_subfolder&id="+tree.getFolder();
                } else if(_action == 'edit') {
                    this.location.href = "edit?tab=tab_metadata&id="+tree.getFolder();
                } else if(_action == 'delete') {
                    if(confirm('"""+t(lang(req), "delete_folder_question")+"""')) {
                        src = tree.getFolder();
                        openWindow('edit_action?src='+src+'&action=delete&ids='+src, 300, 200);
                    }  
                } else if(_action == "clear_trash") {
                    if(confirm('"""+t(lang(req), "clear_trash_question")+"""')) {
                        src = tree.getFolder();
                        openWindow('edit_action?src='+src+'&action=clear_trash&ids='+src, 300, 200);
                    }
                } else {
                    idselection = tree.getFolder();
                    action = _action;
                    this.buttons.document.getElementById("buttonmessage").innerHTML = '&dArr; """+t(lang(req),"select_target_dir")+""" &dArr;';
                }
            }

            function setObjectAction(_action)
            {
                if(_action == 'upload') {
                    reloadPage('"""+uploaddir.id+"""','');
                    return 0;
                } else if(_action == 'import') {
                    reloadPage('"""+importdir.id+"""','');
                    return 0;
                } else if(_action == "edit") {
                    var ids = content.getAllObjectsString();
                    if(ids == '') {
                        reloadPage(tree.getFolder(),'');
                    } else {
                        var src = tree.getFolder();
                        this.content.location.href = "edit_content?ids="+ids+"&src="+src+"&tab=tab_metadata";
                        r = ""+Math.random()*10000;
                        this.buttons.location.href = "edit_buttons?ids="+ids+"&r="+r;
                    }
                    return 0;
                } else if(_action == "editsingle") {
                    var ids = content.getAllObjectsString();
                    if(ids == '') {
                        reloadPage(tree.getFolder(),'');
                    } else {
                        this.content.location.href = "edit_content?ids="+content.getFirstObject()+"&nodelist="+ids+"&tab=tab_metadata";
                        r = ""+Math.random()*10000;
                        this.buttons.location.href = "edit_buttons?ids="+ids+"&r="+r;
                    }
                    return 0;
                } else if(_action == "delete") {
                    var ids = content.getAllObjectsString();
                    if(ids == '') {
                        reloadPage(tree.getFolder(),'');
                    } else {
                        if(confirm('"""+t(lang(req), "delete_object_question")+"""')) {
                            var src = tree.getFolder();
                            openWindow('edit_action?src='+src+'&action=delete&ids='+ids, 300, 200);
                        }
                    }
                    return 0;
                } else {
                    idselection = content.getAllObjectsString();
                    if(idselection) {
                        action = _action;
                    } else {
                        action = "";
                        return 0;
                    }
                    this.buttons.document.getElementById("buttonmessage").innerHTML = '&dArr; """+t(lang(req),"select_target_dir")+""" &dArr;';
                    return 1;
                }
            }
            function reloadTree(id)
            {
                var src;
                if(id) {
                    src = id;
                } else {
                    src = tree.getFolder();
                }
                r = ""+Math.random()*10000;
                this.tree.location.href = "edit_tree?id="+src+"&r="+r+"#"+src;
            }
            function reloadPage(id, id_to_open)
            {
                action = "";
                idselection = "";
                s = "";
                if(id_to_open) {
                    s = "tree_unfold="+id_to_open+"&";
                }
                r = ""+Math.random()*10000;
                this.tree.location.href = "edit_tree?"+s+"id="+id+"&r="+r+"#"+id;
                //this.tree.location.reload();

                this.content.location.href = "edit_content?id="+id+"&r="+r;
                this.buttons.location.href = "edit_buttons?id="+id+"&r="+r;
            }
            function reloadURL(url)
            {
                this.location.href = url;
            }

            function openWindow(fileName, width, height)
            { 
                win1 = window.open(fileName,'browsePopup','screenX=50,screenY=50,width='+width+',height='+height+',directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=no'); 
                win1.focus();
            } 
            function setFolder(folderid)
            {
                var src = tree.getFolder();
                if(action=="") {
                    this.content.location.href = "edit_content?id="+folderid;
                    this.buttons.location.href = "edit_buttons?id="+folderid;
                } else {
                    openWindow('edit_action?src='+src+'&action='+action+'&dest='+folderid+'&ids='+idselection, 300, 200);
                }
            }
            """

    req.writeTAL("web/edit/edit.html", {"id":id, "tab":(tab and "&tab="+tab) or "", "script":script}, macro="edit_main")

    
def getBreadcrumbs(menulist, tab):
    for menuitem in menulist:
        for item in menuitem.getItemList():
            if item[1]==tab or tab.startswith(item[1]) or item[1].startswith(tab):
                return [menuitem.getName(),"*"+ item[1]]
    return [""]

def filterMenu(menuitems, user):

    hide = users.getHideMenusForUser(user)
    ret = list()
    for menu in menuitems:
        i = []
        for item in menu.getItemList():
            if item[2][4:] not in hide:
                i.append(item)
            else:
                print "hide editor menu:", item[2]
        menu.item = i
        ret.append(menu)
    return ret
    
def handletabs(req, ids, tabs):
    user = users.getUserFromRequest(req)

    n = tree.getNode(ids[0])
    if n.type=="workflows":
        n = tree.getRoot()

    menu = filterMenu(n.getEditMenuTabs(), user)

    spc = [Menu("sub_header_frontend", "sub_header_inquest_title","#", "../", target="_parent")]  
    if user.isAdmin():
        spc.append(Menu("sub_header_administration", "sub_header_administration_title","#", "../admin", target="_parent"))
        
    if user.isWorkflowEditor():
        spc.append(Menu("sub_header_workflow", "sub_header_workflow_title","#", "../publish", target="_parent"))

    currenttab = req.params.get("tab", tabs)
    breadcrumbs = getBreadcrumbs(menu, currenttab)
    req.writeTAL("web/edit/edit.html", {"user":user, "ids":ids, "idstr":",".join(ids), "menu":menu, "breadcrumbs":breadcrumbs, "spc":spc}, macro="edit_tabs")
    return currenttab

def error(req):
    req.writeTAL("<tal:block tal:replace=\"errormsg\"/>",{"errormsg":req.params.get("errmsg","")} , macro="edit_errorpage")
    return athana.HTTP_OK

def openErrorPage(req, errormsg):
    req.write("""
    <html>
    <head>
        <script language="javascript">
            function openWindow(fileName, width, height)
            { 
                var win1 = window.open(fileName,'errorPopup','screenX=50,screenY=50,width='+width+',height='+height+',directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=no'); 
                win1.focus();
            } 
            function o()
            {
                openWindow('edit_error?errmsg=%s', 300, 200);
                location.href = "edit_buttons";
            }
        </script>
    </head>
    <body onload="setTimeout(o())">
        <h1>%s</h1>
    </body>
    </html>""" % (urllib.quote(errormsg), errormsg))
    return athana.HTTP_OK


def getIDs(req):
    # update nodelist, if necessary
    if "nodelist" in req.params:
        nodelist = []
        for id in req.params["nodelist"].split(","):
            nodelist.append(tree.getNode(id))
        req.session["nodelist"] = EditorNodeList(nodelist)

    # look for one "id" parameter, containing an id or a list of ids
    try:
        id = req.params["id"]
    except KeyError:
        pass
    else:
        idlist = id.split(",")
        if idlist != ['']:
            return idlist

    # look for a pattern, a source folder and an id list
    try:
        ids = req.params["ids"]
    except KeyError:
        ids = ""
    try:
        srcid = req.params["src"]
        if srcid == "":
            raise KeyError
        src = tree.getNode(srcid)
    except KeyError:
        src = None

    idlist = ids.split(',')
    if idlist == ['']:
        idlist = []

    return idlist

def nodeIsChildOfNode(node1,node2):
    if node1.id == node2.id:
        return 1
    for c in node2.getChildren():
        if nodeIsChildOfNode(node1, c):
            return 1
    return 0

def action(req):
    access = AccessData(req)
    user = users.getUserFromRequest(req)
    trashdir = getTrashDir(user)

    if not access.user.isEditor():
        req.write("""permission denied""")
        return
        
        
    if req.params.get("tab")=="tab_publish":
        edit_publish(req, [req.params.get("id")])
        return
    
    srcid = req.params["src"]
    try:
        src = tree.getNode(srcid)
    except:
        req.writeTAL("web/edit/edit.html", {"edit_action_error":srcid}, macro="edit_action_error")
        return
  
    newfolder = req.params.get("newfolder", "")
    is_collection = 0
    if not newfolder:
        is_collection = 1
        newfolder = req.params.get("newcollection", "")

    if newfolder != "":
        node = tree.getNode(srcid)
        if not access.hasWriteAccess(node):
            req.write("""
                <html>
                <head>
                    <script language="javascript">
                        opener.reloadURL('edit?id="""+node.id+"""');
                    </script>
                </head>
                <body>
                    <h2>""" + t(lang(req), "edit_error") + """</h2>
                    """ + t(lang(req), "edit_error_msg1") + """
                </body>
                </html>
            """)
            return;

        if node.type == "collections":
            # always create a collection in the uppermost hierarchy- independent on
            # what the user requested
            newnode = node.addChild(tree.Node(name=newfolder, type="collection"))
        else:
            if is_collection:
                if node.type != "collection" and node.type != "collections":
                    req.writeTAL("web/edit/edit.html", {"errormsg":"can't create a collection below a node of type "+str(node.type)}, macro="edit_errorpage")
                    return
                newnode = node.addChild(tree.Node(name=newfolder, type="collection"))
            else:
                newnode = node.addChild(tree.Node(name=newfolder, type="directory"))
        
        newnode.set("creator", user.getName())
        newnode.set("creationtime",  str(time.strftime( '%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
        
        req.write("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">
        <html>
          <head>
            <script language="javascript">
                //opener.reloadURL('edit?tab=Metadaten&id="""+newnode.id+"""');
                opener.reloadURL('edit?tab=tab_metadata&id="""+newnode.id+"""');
                this.close();
            </script>
          </head>
        </html>
        """)
        return;

    try:
        destid = req.params["dest"]
        dest = tree.getNode(destid)
        folderid = destid
    except:
        destid = None
        dest = None
        folderid = srcid
    
    action = req.params["action"] 

    idlist = getIDs(req)
    
    req.write("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">
        <html>
        <head>
            <META http-equiv="Content-Type" content="text/html; charset=UTF-8">
            <meta content="text/html;charset=UTF-8" http-equiv="content-type">
            <script language="javascript">
                function returnValue(srcid) 
                {
                    window.close();
                    opener.reloadPage(srcid, '');
                }
            </script>
        </head>
        <body>""")
            
    req.writeTALstr('<span i18n:translate="edit_action_msg">Die Aktion <b i18n:name="action">'+ t(lang(req), action) + '</b> wird ausgef&uuml;hrt</span>',{})
    
    try:

        print "srcid",srcid,tree.getNode(srcid).getName()
        if destid:
            print "destid",destid,tree.getNode(destid).getName()
        print "ids",idlist

        if action=="clear_trash":
            for n in trashdir.getChildren():
                trashdir.removeChild(n)
            print "remove all nodes from users trash"

        for id in idlist:
            obj = tree.getNode(id)
            mysrc = src
            if isDirectory(obj):
                mysrc = obj.getParents()[0]

            if action == "delete":
                if access.hasWriteAccess(mysrc) and access.hasWriteAccess(obj):
                    if mysrc.id==trashdir.id:
                        print "source node is trashbox!"
                    else:
                        print "Remove",obj.id,"from",mysrc.id
                        mysrc.removeChild(obj)
                        trashdir.addChild(obj)
                else:
                    print "No write access to",mysrc.id,"!"
            elif action == "move":
                print mysrc.id,'==',id,'==>',dest.id
                if dest != mysrc and \
                   access.hasWriteAccess(mysrc) and \
                   access.hasWriteAccess(dest) and \
                   access.hasWriteAccess(obj) and \
                   isDirectory(dest):
                    if not nodeIsChildOfNode(dest,obj):
                        print "Move",obj.id,"from",mysrc.id,"to",dest.id
                        mysrc.removeChild(obj)
                        dest.addChild(obj)
                    else:
                        print "Couldn't move",obj.id,"from",mysrc.id,"to",dest.id,":",dest.id,"is child of",obj.id
                mysrc = None
            elif action == "copy":
                if dest != mysrc and \
                   access.hasReadAccess(mysrc) and \
                   access.hasWriteAccess(dest) and \
                   access.hasWriteAccess(obj) and \
                   isDirectory(dest):
                    if not nodeIsChildOfNode(dest,obj):
                        print "Copy",obj.id,"from",mysrc.id,"to",dest.id
                        dest.addChild(obj)
                    else:
                        print "Couldn't copy",obj.id,"from",mysrc.id,"to",dest.id,":",dest.id,"is child of",obj.id
                mysrc = None
        if not mysrc:
            mysrc = src

        req.write("""<script language="javascript">returnValue('"""+mysrc.id+"""');</script>""")
    except:
        req.write("""<h1>"""+t(lang(req),"edit_error")+"""</h1>""")
        req.write(str(sys.exc_info()[0]) or "")
        req.write("<br>")
        req.write(str(sys.exc_info()[1]) or "")
        req.write("""
        <script language="javascript">
            opener.reloadPage('"""+srcid+"""', '');
        </script>
        """)

    req.write("""</body></html>""")


def isDirectory(node):
    return node.type == "directory" or node.type == "root" or node.type == "collection" or node.type == "collections"

def showPaging(req, tab, ids):
    nodelist = req.session.get("nodelist", None)
    if nodelist and len(ids)==1:
        previd = nodelist.getPrevious(ids[0])
        if previd:
            link1 = '<a href="/edit/edit_content?id=%s&tab=%s"><img border="0" src="/img/pageleft.gif"></a>' % (previd, tab)
        else:
            link1 = '&nbsp;'
        nextid = nodelist.getNext(ids[0])
        if nextid:
            link2 = '<a href="/edit/edit_content?id=%s&tab=%s"><img border="0" src="/img/pageright.gif"></a>' % (nextid, tab)
        else:
            link2 = '&nbsp;'

        req.write("""
        <table width="100%%" style="padding-top:5px;margin-top:24px">
        <tr width="100%%"><td style="width:50px">%s</td><td align="center" width="100%%" style="text-align:center">%s</td><td style="width:50px">%s</td></tr>
        </table>
        """ % (link1, nodelist.getPositionString(ids[0]), link2))
    else:
        req.write("""
        <table width="100%%" style="padding-top:5px;margin-top:24px">
        <tr width="100%%"><td>&nbsp;</td></tr>
        </table>""")
        

def content(req):
    access = AccessData(req)

    # remove all caches for the frontend area- we might make changes there
    for sessionkey in ["contentarea", "navframe"]:
        try:
            del req.session[sessionkey]
        except:
            pass

    ids = getIDs(req)

    print req.params
    if req.params.get("type","")== "help":
        if req.params.get("tab","")=="tab_upload":   
            upload_help(req)
        return

    if len(ids)==0:
        req.writeTALstr('<i i18n:translate="edit_noselection">nichts ausgew&auml;hlt</i>',{})
        return

    req.write("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">""")
    if req.params.get("tab", "") == "tab_view":
        req.write("""
            <html>
            <head>
              <META http-equiv="Content-Type" content="text/html; charset=UTF-8">
              <meta content="text/html;charset=UTF-8" http-equiv="content-type">
              <link rel="stylesheet" href="/css/editor.css">
              <link rel="stylesheet" href="/css/edit_style.css">
              <script type="text/javascript" src="/js/mediatum.js"></script>
            </head>""")
        req.write("""<body>""")
    else:
        req.write("""
            <html>
            <head>
              <META http-equiv="Content-Type" content="text/html; charset=UTF-8">
              <meta content="text/html;charset=UTF-8" http-equiv="content-type">
              <link rel="stylesheet" href="/css/editor.css">
              <link rel="stylesheet" href="/css/edit_style.css">
              <script type="text/javascript" src="/js/editor.js"></script>
              <script type="text/javascript" src="/js/admin.js"></script>
              <script type="text/javascript" src="/js/mediatum.js"></script>
                                  
              <script language="javascript"> 
                  var allobjects = new Array();
              """)

        req.write("""
                  function getAllObjectsString()
                  {
                      var s = "";
                      var first = 1;
                      for(var i in allobjects) {
                          if(allobjects[i]) {
                              if(first!=1) s += ",";
                              s += i; first = 0;
                          }
                      }
                      return s;
                  }
                  function getFirstObject()
                  {
                      for(var i in allobjects) {
                          if(allobjects[i]) {
                              return i;
                          }
                      }
                  }
                  function clearObjects()
                  {
                      for(var i in allobjects) {
                          allobjects[i] = 0;
                      }
                  }
              </script>
                                  <!--[if IE]>
        <style type="text/css">
        ul#nav li ul  {
        filter: alpha(opacity=95);
        }
        </style>
        <![endif]-->
            </head>""")
        req.write("""<body>""")
    
    user = users.getUserFromRequest(req)
    uploaddir = getUploadDir(user)
    importdir = getImportDir(user)

    node = tree.getNode(ids[0])
    tabs = "tab_content"
    if node.type == "root":
        tabs = "tab_content"
    elif node.id == uploaddir.id:
        tabs = "tab_upload"
    elif node.id == importdir.id:
        tabs = "tab_import"
    elif hasattr(node, "getDefaultEditTab"):
        tabs = node.getDefaultEditTab()

    current = handletabs(req, ids, tabs)
    if not access.user.isEditor():
        req.writeTALstr('<div class="MainMenu"><br/><br/><p i18n:translate="edit_error_msg" class="error" style="text-align:center">TEXT <span i18n:name="link"><a i18n:translate="edit_linktext" href="../login" target="_parent">TEXT</a></span></p></div>', {})
        req.write("</body>")
        return   

    showPaging(req, current, ids)
    req.write('<div style="margin:5px 5px 5px 5px;border:1px solid silver;padding: 4px">')
    
    # some tabs operate on only one file
    if current == "tab_files" or current == "tab_editor" or current == "tab_view" or current == "tab_upload":
        ids = ids[0:1]

    # display current images
    if "image" or "doc" in tree.getNode(ids[0]).type:
        req.writeTALstr('<b i18n:translate="edit_taboverview_header">Ausgew&auml;hlt/in Bearbeitung:</b><br/>',{})

        if current != "tab_view":
            req.write("""<script language="javascript">\n""")
            req.write("""clearObjects();\n""")

            for id in ids:
                req.write("""allobjects['%s'] = 1;\n""" % id)

            req.write("""
                function fullSizeWindow(id,width,height)
                {
                    var win1 = window.open('/fullsize?id='+id,'fullsize','width='+width+',height='+height+',directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=1'); 
                    win1.focus();
                }
            """)

            req.write("""</script>\n""")
            req.write("""<table border="0"><tr>""")
            for id in ids:
                node = tree.getNode(id)
                if hasattr(node,"show_node_image"):
                    req.write("""<td align="center">""")
                    if not isDirectory(node):
                        req.write("""<a href="javascript:fullSizeWindow('"""+id+"""','"""+str(node.get("width"))+"""','"""+str(node.get("height"))+"""')">""")

                    req.write(node.show_node_image())

                    if not isDirectory(node):
                        req.write("""</a>""")

                    req.write("""</td>""")
                    req.write("""<td width="20">&nbsp;</td>""")
            req.write("""</tr></table>""")
    else: # or current directory
        req.writeTALstr('<b i18n:translate="edit_actual_dir">Aktuelles Verzeichnis:</b><br>',{})
        n = tree.getNode(ids[0])
        first = 1
        s = ""
        while n:
            if not first:
                s = '<b>-&gt;</b>' + s
            s = '<a target="frame" href="/edit?id=%s">%s</a>' % (n.id,n.name) + s
            first = 0
            p = n.getParents()
            if p: n = p[0]
            else: n = None
        req.write('<div style="margin-left: 20px">'+s+'</div>')
        req.write('<hr>')

    if current == "tab_view":
        if hasattr(node, "show_node_big"):
            req.writeTALstr("""
            <span i18n:translate="edit_tabarea_msg1"/>
            <br>
            <b i18n:translate="hint"></b><span i18n:translate="edit_tabarea_msg2"/><br/>
            <hr/>
            """, {})
            req.write(node.show_node_big(req))
        else:
            req.writeTALstr("""
            <span i18n:translate="edit_object_not_viewable"/><br>
            """, {})
    elif current == "tab_acls":
        edit_acls(req,ids)
    elif current == "tab_workflow":
        edit_workflow(req,ids)
    elif current == "tab_search":
        edit_search(req,ids)
    elif current == "tab_subfolder":
        #edit_sort(req,ids)
        edit_subfolder(req,ids)
    elif current == "tab_sort":
        edit_sortfiles(req,ids)
    elif current == "tab_searchmask":
        edit_searchmask(req,ids)
    elif current == "tab_classes":
        edit_classes(req,ids)
    elif current == "tab_license":
        edit_license(req,ids)
    elif current == "tab_files":
        edit_files(req,ids)
    elif current == "tab_content":
        if node.type == "directory" or node.type.startswith("collection"):
            showdir(req,node)
    elif current == "tab_editor":
        found=False
        for f in node.getFiles():
            if f.mimetype == 'text/html':
                edit_editor(req, node, f)
                found=True
        if not found:
            edit_editor(req, node, None)
 
    elif current == "tab_metadata":
        edit_metadata(req, ids)
    elif current == "tab_upload":
        edit_upload(req, ids)
    elif current == "tab_import":
        edit_import(req, ids)
    elif current == "tab_globals":
        req.write("")
    elif current == "tab_lza":
        edit_lza(req, ids)
    elif current == "tab_logo":
        edit_logo(req, ids)
    elif current == "tab_publish":
        edit_publish(req, ids)
    else:
        req.write("<b>Unknown tab</b> '%s'" % current)
    
    req.write('</div')
    req.write('</body>')
    req.write('</html>')
    

def buttons(req):

    if "id" in req.params:
        node = tree.getNode(req.params["id"])
    else:
        node = None

    req.write("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">
        <html>
        <head>
          <META http-equiv="Content-Type" content="text/html; charset=UTF-8">
          <meta content="text/html;charset=UTF-8" http-equiv="content-type">
          <link rel="stylesheet" href="/css/editor.css">
          <link rel="stylesheet" href="/css/edit_style.css">
          <script language="javascript">
             function disableMoveDeleteOperations() {
                 this.document.getElementById("field_move").disabled = true;
                 this.document.getElementById("field_delete").disabled = true;
             }
             function reset() {
                 this.document.getElementById("field_move").enabled = true;
                 this.document.getElementById("field_delete").enabled = true;
             }
          </script>
        </head>
        <body>
            <div id="logocontainer">
                &nbsp;
            </div>
            <div class="topmenucontainer">
                <span>&nbsp;</span>
            </div>
        """)

    if not node:
        dirtype = ""
        newcoll = None
        newdir = None
    elif isCollection(node):
        dirtype = t(req, "collection")+":"
        newcoll = t(req, "edit_action_new")+": " + t(req, "collection")
        newdir = t(req, "edit_action_new")+": " + t(req, "directory")
    else:
        dirtype = t(req, "directory")+":"
        newcoll = None
        newdir = t(req, "edit_action_new")+": " + t(req, "directory")

    if node:
        nodename = node.name
    else:
        nodename = ""
    
    access = AccessData(req)
    if not access.user.isEditor():
        req.write("</body></html>")
        return

    req.writeTALstr("""
            <table cellspacing="0" cellpadding="0">
            </table>
                <form name="changeaction">
                     <b i18n:translate="edit_files">Dateien:</b><br/>
                     <select id="groupaction" onChange="if(!parent.setObjectAction(this.value)) {this.value='none'}" name="groupaction" style="width:250px">
                         <option value="none">---</option>                      
                         <option value="upload" i18n:translate="edit_action_file_upload">_</option>
                         <option value="import" i18n:translate="edit_action_file_import">_</option>
                         <option id="field_move" value="move" i18n:translate="edit_action_file_move">Verschieben nach...</option>
                         <option value="copy" i18n:translate="edit_action_file_copy">Kopieren nach...</option>
                         <option id="field_delete" value="delete" i18n:translate="edit_action_file_delete">L&ouml;schen</option>
                         <option value="edit" i18n:translate="edit_action_file_edit">Gleichzeitig Bearbeiten</option>
                         <option value="editsingle" i18n:translate="edit_action_file_editsingle">Einzeln Bearbeiten</option>
                     </select><br/>
                     <b tal:attributes="alt name; title name" tal:content="type"/><br/>
                     <select id="folderaction" onChange="parent.setFolderAction(this.value)" name="folderaction" style="width:250px">
                         <option value="">---</option>
                         <option value="newcollection" tal:condition="newcoll" tal:content="newcoll">_</option>
                         <option value="newfolder" tal:condition="newdir" tal:content="newdir">_</option>
                         <option value="edit" i18n:translate="edit_action_dir_edit">_</option>
                         <option value="move" i18n:translate="edit_action_dir_move">_</option>
                         <option value="sortsubfolders" i18n:translate="edit_action_dir_sort">_</option>
                         <!--<option value="copy" i18n:translate="edit_action_dir_copy">_</option>-->
                         <option value="delete" i18n:translate="edit_action_dir_del">_</option>
                         <option value="clear_trash" i18n:translate="edit_action_clear_trash">_</option>
                     </select>
                 </form>
                 <p id="buttonmessage" style="color:red">&nbsp;</p>
                 """,{"type": dirtype, "newdir": newdir, "newcoll": newcoll, "name": nodename})

    req.write("""<hr/></body></html>""")

def showtree(req):
    access = AccessData(req)
    user = users.getUserFromRequest(req)
    if not user.isEditor():
        req.writeTAL("web/edit/edit.html", {}, macro="edit_notree_permission")
        return

    # scroll the tree to either the current id or the parent id
    # (or to what was requested via the scrollid parameter)

    currentid = req.params.get("id",tree.getRoot().id)
    p = tree.getNode(currentid).getParents()
    if len(p): parentid = p[0].id
    else: parentid = None
    scrollid = req.params.get("scrollid",parentid)
    if scrollid is None:
        scrollid = currentid

    # make sure the scrollid and currentid are never too far
    # from each other
    if currentid != scrollid:
        try:
            unfoldedids = req.session["lefttreenodes"]
        except:
            unfoldedids = {}
        def countDistance(node, distance):
            if node.id == currentid:
                return 1
            distance[0] = distance[0] + 1
            if node.id in unfoldedids and unfoldedids[node.id]:
                for c in node.getChildren().sort("name"):
                    dist = countDistance(c, distance)
                    if dist:
                        return 1
            return 0
        dist = [0]
        if countDistance(tree.getNode(scrollid),dist):
            if dist[0] > 24:
                scrollid = currentid

    script ="""var currentfolder = '"""+currentid+"""';
        function setFolder(id)
        {
            img = document.images['img'+id];
            if(currentfolder != "") {
                lastimg = document.images['img'+currentfolder];
                if(lastimg) {
                    lastimg.src = "/img/mark_empty.png";
                    lastimg.title = "";
                }
            }
            if(img) {
                img.src = "/img/mark_arrow.png";
                img.title = "Selektierter Ordner ("+id+")";
            }
            parent.setFolder(id);
            currentfolder = id;
        }
        function getFolder() 
        {
            return currentfolder;
        }
        function openNode(link,id)
        {
            document.location.href = link + "&id="+currentfolder + "&scrollid=" + id;
        }"""

    c = [""]
    def f(req,node,objnum,link,indent,type):
        indent *= 10
        if objnum and node.getType().getName()!="root":
            items = ' ('+str(objnum)+')'
        else:
            items = ''

        nodename = node.name
        try: nodename = node.getLabel()
        except: 
            log.logException()

        c[0] += '<a name="'+str(node.id)+'"/>'

        c[0] += '<div class="line">'
        c[0] += ' <div class="name" style="padding-left: '+str(indent)+'px">'
        if node.id != currentid:
            c[0] += '<img id="img%s" src="/img/mark_empty.png"/>' % (node.id)
        else:
            c[0] += '<img id="img%s" title="%s" src="/img/mark_arrow.png"/>' % (node.id, "Selektierter Ordner ("+node.id+")")
        title = 'title="'+nodename + ' (ID'+node.id+')"'

        if access.hasWriteAccess(node):
            if isCollection(node):
                color = 'class="coll_canwrite"'
            else:
                color = 'class="dir_canwrite"'
        else:
            if isCollection(node):
                color = 'class="coll_canread"'
            else:
                color = 'class="dir_canread"'

        if type == 1:
            c[0] += "<a title=\""+t(lang(req),"edit_classes_close_title")+"\" href=\"javascript:openNode('"+link+"','"+node.id+"')"+"\"><img src=\"/img/edit_box1.gif\" border=\"0\"/></a>"
            c[0] += "<a "+color+" "+title+" href=\"javascript:setFolder('"+node.id+"')\">&nbsp;" + nodename+items+"</a>"
        elif type == 2:
            c[0] += "<a title=\""+t(lang(req),"edit_classes_open_title")+"\" href=\"javascript:openNode('"+link+"','"+node.id+"')"+"\"><img src=\"/img/edit_box2.gif\" border=\"0\"/></a>"
            c[0] += "<a "+color+" "+title+" href=\"javascript:setFolder('"+node.id+"')\">&nbsp;" + nodename+items+"</a>"
        elif type == 3:
            c[0] += "<img src=\"/img/edit_box3.gif\" border=\"0\"/>"
            c[0] += "<a "+color+" "+title+" href=\"javascript:setFolder('"+node.id+"')\">&nbsp;" + nodename+items+"</a>"
        c[0] += " </div>"
        c[0] += "</div>"
   
    node = tree.getNode(currentid)
    o = None
    if len(node.getParents()):
        o = [node.getParents()[0]]


    home_omitroot = 1
    if len(access.filter(tree.getRoot("home").getChildren())) > 1:
        home_omitroot = 0

    content = [""]
    writetree(req, tree.getRoot("home"), f, "", openednodes=o, sessionkey="lefttreenodes", omitroot=home_omitroot)
    writetree(req, tree.getRoot("collections"), f, "", openednodes=o, sessionkey="lefttreenodes", omitroot=0)
    writetree(req, tree.getRoot("navigation"), f, "", openednodes=o, sessionkey="lefttreenodes", omitroot=1)

    req.writeTAL("web/edit/edit.html", {"script":script, "scrollid":scrollid, "content":c[0]}, macro="edit_tree")

def flush(req):
    tree.flush()
    req.write("<p>Caches have been flushed</p>")
