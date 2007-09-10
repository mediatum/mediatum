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
import core.translation
import core.athana as athana
import utils.log
from core.acl import AccessData
from utils.utils import Link

from edit_common import *
from edit_acls import edit_acls
from edit_metadata import edit_metadata
from edit_classes import edit_classes
from edit_files import edit_files
from edit_upload import edit_upload, upload_help
from edit_search import edit_search
from edit_sort import edit_sort
from edit_editor import edit_editor
from edit_workflow import edit_workflow
from edit_license import edit_license
from core.translation import lang, t


def frameset(req):
    id = req.params.get("id", tree.getRoot().id)
    tab = req.params.get("tab", None)

    user = users.getUserFromRequest(req)
    if not user.isEditor():
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return

    uploaddir = getUploadDir(user)
    faultydir = getFaultyDir(user)

    currentdir = tree.getNode(id)
    script="""
            var idselection = "";
            var action = "";

            function setFolderAction(_action)
            {
                if(_action == 'newfolder') {
                    openWindow("edit_action?newfolder=Neuer%20Ordner&src="+tree.getFolder(),300,200);
                } else if(_action == 'sortsubfolders') {
                    this.location.href = "edit?tab=tab_subfolder&id="+tree.getFolder();
                } else if(_action == 'edit') {
                    this.location.href = "edit?tab=tab_meta&id="+tree.getFolder();
                } else if(_action == 'delete') {
                    if(confirm('"""+t(lang(req), "delete_folder_question")+"""')) {
                        src = tree.getFolder();
                        openWindow('edit_action?src='+src+'&action=delete&ids='+src, 300, 200);
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
                } else if(_action == "edit") {
                    var ids = content.getAllObjectsString();
                    if(ids == '') {
                        reloadPage(tree.getFolder(),'');
                    } else {
                        var src = tree.getFolder();
                        this.content.location.href = "edit_content?ids="+ids+"&src="+src+"&tab=tab_meta";
                        r = ""+Math.random()*10000;
                        this.buttons.location.href = "edit_buttons?r="+r;
                    }
                    return 0;
                } else if(_action == "editsingle") {
                    var ids = content.getAllObjectsString();
                    if(ids == '') {
                        reloadPage(tree.getFolder(),'');
                    } else {
                        this.content.location.href = "edit_content?ids="+content.getFirstObject()+"&nodelist="+ids+"&tab=tab_meta";
                        r = ""+Math.random()*10000;
                        this.buttons.location.href = "edit_buttons?r="+r;
                    }
                    return 0;
                } else if(_action == "delete") {
                    var ids = content.getAllObjectsString();
                    if(ids == '') {
                        reloadPage(tree.getFolder(),'');
                    } else {
                        var src = tree.getFolder();
                        openWindow('edit_action?src='+src+'&action=delete&ids='+ids, 300, 200);
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
                this.buttons.location.href = "edit_buttons?r="+r;
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
                } else {
                    openWindow('edit_action?src='+src+'&action='+action+'&dest='+folderid+'&ids='+idselection, 300, 200);
                }
            }
            """

    req.writeTAL("web/edit/edit.html", {"id":id, "tab":(tab and "&tab="+tab) or "", "script":script}, macro="edit_main")

def handletabs(req, ids, tabs):
    user = users.getUserFromRequest(req)

    l = [Link("/logout", t(lang(req),"sub_header_logout_title"), t(lang(req),"sub_header_logout"), "_parent")]
    if config.get("user.guestuser") == user.getName():
        l = [Link("/login", t(lang(req),"sub_header_login_title"), t(lang(req),"sub_header_login"), "_parent")]

    l += [Link("/", t(lang(req),"sub_header_inquest_title"), t(lang(req),"sub_header_inquest"), "_parent")]

    if user.isAdmin():
        l += [Link("/admin", t(lang(req),"sub_header_administration_title"), t(lang(req),"sub_header_administration"), "_parent")]
    
    if user.isWorkflowEditor():
        l += [Link("/publish/", t(lang(req),"sub_header_workflow_title"), t(lang(req),"sub_header_workflow"))]

    if config.get("user.guestuser") != user.getName() and "c" in user.getOption():
        l += [Link("/display_changepwd", t(lang(req),"sub_header_changepwd_title"), t(lang(req),"sub_header_changepwd"), "_parent")]

    idstr=""
    for id in ids:
        if idstr:
            idstr+=","
        idstr+=id
    currenttab = req.params.get("tab", tabs[0])
    
    req.writeTAL("web/edit/edit.html", {"user":user, "menuitems":l, "tabs":tabs, "ids":ids, "idstr":idstr, "currenttab":currenttab}, macro="edit_tabs")

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

    if not access.user.isEditor():
        req.write("""permission denied""")
        return
    
    srcid = req.params["src"]
    try:
        src = tree.getNode(srcid)
    except:
        req.writeTAL("web/edit/edit.html", {"edit_action_error":srcid}, macro="edit_action_error")
        return
   
    newfolder = req.params.get("newfolder", "")
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

        if node.type == "root":
            newnode = node.addChild(tree.Node(name=newfolder, type="collection"))
        else:
            newnode = node.addChild(tree.Node(name=newfolder, type="directory"))
        user = users.getUserFromRequest(req)
        newnode.set("creator", user.getName())
        newnode.set("creationtime",  str(time.strftime( '%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
        
        req.write("""
        <html>
          <head>
            <script language="javascript">
                //opener.reloadURL('edit?tab=Metadaten&id="""+newnode.id+"""');
                opener.reloadURL('edit?tab=tab_meta&id="""+newnode.id+"""');
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

        for id in idlist:
            obj = tree.getNode(id)
            mysrc = src
            if isDirectory(obj):
                mysrc = obj.getParents()[0]

            if action == "delete":
                if access.hasWriteAccess(mysrc) and access.hasWriteAccess(obj):
                    print "Remove",obj.id,"from",mysrc.id
                    mysrc.removeChild(obj)
                else:
                    print "No write access to",mysrc.id,"!"
            elif action == "move":
                print mysrc.id,'==',id,'==>',dest.id
                if dest != mysrc and \
                   access.hasWriteAccess(mysrc) and \
                   access.hasWriteAccess(dest) and \
                   access.hasWriteAccess(obj) and \
                   (dest.type=="directory" or obj.type=="directory"):
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
                   (dest.type=="directory" or obj.type=="directory"):
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
        <table width="100%%">
        <tr width="100%%"><td>%s</td><td align="center" width="100%%">%s</td><td>%s</td></tr>
        </table>
        """ % (link1, nodelist.getPositionString(ids[0]), link2))

def content(req):
    access = AccessData(req)
    if not access.user.isEditor():
        req.writeTALstr('<span i18n:translate="edit_nopermission">Keine Berechtigung</span>',{})
        return

    ids = getIDs(req)

    if req.params.get("type","")== "help":
        if req.params.get("tab","")=="tab_upload":   
            upload_help(req)
        return

    if len(ids)==0:
        req.writeTALstr('<i i18n:translate="edit_noselection">nichts ausgew&auml;hlt</i>',{})
        return

    if req.params.get("tab", "") == "tab_view":
        req.write("""
            <html>
            <head>
              <META http-equiv="Content-Type" content="text/html; charset=UTF-8">
              <meta content="text/html;charset=UTF-8" http-equiv="content-type">
              <link rel="stylesheet" href="/css/editor.css">
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
            </head>""")
        req.write("""<body style="background-color: #ffffff">""")

    node = tree.getNode(ids[0])
    if isDirectory(node):
        tabs = ["tab_content", "tab_html", "tab_search", "tab_subfolder", "tab_meta", "tab_acls", "tab_license", "tab_techmeta", "tab_view"]
        
        if node.name=="Uploads":
            tabs = ["tab_upload"] + tabs[1:]

    else:
        tabs = ["tab_meta", "tab_acls", "tab_classes", "tab_techmeta", "tab_view"]
        
    current = handletabs(req, ids, tabs)

    showPaging(req, current, ids)

    req.write('<div style="margin: 20px">')
    
    # some tabs operate on only one file
    if current == "tab_techmeta" or current == "tab_html" or current == "tab_view" or current == "tab_upload":
        ids = ids[0:1]

    # display current images
    if "image" or "doc" in tree.getNode(ids[0]).type:
        req.writeTALstr('<b i18n:translate="edit_taboverview_header">Ausgew&auml;hlt/in Bearbeitung:</b><br>',{})

        if current != "tab_view":
            req.write("""<script language="javascript">\n""")
            req.write("""clearObjects();\n""")
            #try:
            #    req.write("""parent.setSrc('"""+tree.getNode(ids[0]).getParents()[0].id+"""');""")
            #except:
            #    pass

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
                    if node.type!="directory":
                        req.write("""<a href="javascript:fullSizeWindow('"""+id+"""','"""+str(node.get("width"))+"""','"""+str(node.get("height"))+"""')">""")

                    req.write(node.show_node_image())

                    if node.type!="directory":
                        req.write("""</a>""")

                    req.write("""</td>""")
                    req.write("""<td width="20">&nbsp;</td>""")
            req.write("""</tr></table>""")
        req.write('<hr>')
    else: # or current directory
        req.writeTALstr('<b i18n:translate="edit_actual_dir">Aktuelles Verzeichnis:</b><br>',{})
        n = tree.getNode(ids[0])
        first = 1
        s = ""
        while n:
            if not first:
                s = '<b>-&gt;</b>' + s
            s = '<a target="frame" href="edit?id=%s">%s</a>' % (n.id,n.name) + s
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
        edit_sort(req,ids)
    elif current == "tab_classes":
        edit_classes(req,ids)
    elif current == "tab_license":
        edit_license(req,ids)
    elif current == "tab_techmeta":
        edit_files(req,ids)
    elif current == "tab_content":
        if node.type == "directory":
            showdir(req,node)
    elif current == "tab_html":
        found=False
        for f in node.getFiles():
            if f.mimetype == 'text/html':
                edit_editor(req, node, f)
                found=True
        if not found:
            edit_editor(req, node, None)
 
    elif current == "tab_meta":
        edit_metadata(req, ids)
    elif current == "tab_upload":
        edit_upload(req, ids)
    else:
        req.write("<b>Unknown tab</b> '%s'" % current)
    
    req.write('</div')

    req.write("""</body>""")
    req.write("""</html>""")

def buttons(req):

    access = AccessData(req)
    if not access.user.isEditor():
        req.writeTAL('<span i18n:translate="edit_nopermission">Keine Berechtigung</span>',{})
        return

    req.write("""
        <html>
        <head>
          <META http-equiv="Content-Type" content="text/html; charset=UTF-8">
          <meta content="text/html;charset=UTF-8" http-equiv="content-type">
          <link rel="stylesheet" href="/css/editor.css">
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
        <body bgcolor="#ffffff">""")

    req.writeTALstr("""
            <table cellspacing="0" cellpadding="0">
            <tr><td><a i18n:attributes="title sub_header_inquest_title" title="Zur Rechercheoberfl&auml;che wechseln" href="/" target="_parent"><img border="0" height="142" src="/img/mediatum.png"></a></td><td width="100%"><img border="0" width="100%" height="142" src="/img/mediatum_line.png"></td></tr>
            </table>
                <form name="changeaction">
                     <b i18n:translate="edit_files">Dateien:</b><br/>
                     <select id="groupaction" onChange="if(!parent.setObjectAction(this.value)) {this.value='none'}" name="groupaction" style="width:250px">
                         <option value="none">---</option>
                         <option value="upload" i18n:translate="edit_action_file_upload">Hochladen</option>
                         <option id="field_move" value="move" i18n:translate="edit_action_file_move">Verschieben nach...</option>
                         <option value="copy" i18n:translate="edit_action_file_copy">Kopieren nach...</option>
                         <option id="field_delete" value="delete" i18n:translate="edit_action_file_delete">L&ouml;schen</option>
                         <option value="edit" i18n:translate="edit_action_file_edit">Gleichzeitig Bearbeiten</option>
                         <option value="editsingle" i18n:translate="edit_action_file_editsingle">Einzeln Bearbeiten</option>
                     </select><br/>
                     <b i18n:translate="edit_dir">Ordner:</b><br/>
                     <select id="folderaction" onChange="parent.setFolderAction(this.value)" name="folderaction" style="width:250px">
                         <option value="">---</option>
                         <option value="newfolder" i18n:translate="edit_action_dir_new">Neu Anlegen</option>
                         <option value="edit" i18n:translate="edit_action_dir_edit">Bearbeiten</option>
                         <option value="move" i18n:translate="edit_action_dir_move">Verschieben nach...</option>
                         <option value="sortsubfolders" i18n:translate="edit_action_dir_sort">Unterordner sortieren</option>
                         <!--<option value="copy" i18n:translate="edit_action_dir_copy">Kopieren nach...</option>-->
                         <option value="delete" i18n:translate="edit_action_dir_del">L&ouml;schen</option>
                     </select>
                 </form>
                 <p id="buttonmessage" style="color:red">&nbsp;</p>
                 """,{})

    req.write("""<hr></body></html>""")

def showtree(req):
    access = AccessData(req)
    user = users.getUserFromRequest(req)
    if not user.isEditor():
        req.write("""permission denied""")
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
            color = 'class="canwrite"'
        else:
            color = 'class="canread"'

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

    content = [""]
    writetree(req, tree.getRoot("home"), f, "", openednodes=o, sessionkey="lefttreenodes", omitroot=1)
    writetree(req, tree.getRoot("collections"), f, "", openednodes=o, sessionkey="lefttreenodes", omitroot=0)
    writetree(req, tree.getRoot("navigation"), f, "", openednodes=o, sessionkey="lefttreenodes", omitroot=1)

    req.writeTAL("web/edit/edit.html", {"script":script, "scrollid":scrollid, "content":c[0]}, macro="edit_tree")

def flush(req):
    tree.flush()
    req.write("<p>Caches have been flushed</p>")
