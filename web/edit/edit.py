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
import logging
from core.acl import AccessData
from utils.utils import Link, isCollection, Menu, getFormatedString, splitpath, parseMenuString

from edit_common import *
#from edit_search import edit_search
#from edit_sort import edit_sort
#from edit_searchmask import edit_searchmask
#from edit_publish import edit_publish
from core.translation import lang, t
from edit_common import EditorNodeList
from core.datatypes import loadAllDatatypes
from core.tree import getRoot

logger = logging.getLogger('editor')

def frameset(req):
    id = req.params.get("id", tree.getRoot("collections").id)
    tab = req.params.get("tab", None)

    user = users.getUserFromRequest(req)

    uploaddir = getUploadDir(user)
    importdir = getImportDir(user)
    faultydir = getFaultyDir(user)
    trashdir = getTrashDir(user)

    try:
        currentdir = tree.getNode(id)
        
    except tree.NoSuchNodeError:
        currentdir = tree.getRoot("collections")
        req.params["id"] = currentdir.id
        id = req.params.get("id")  
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
                    this.location.href = "edit?tab=subfolder&id="+tree.getFolder();
                } else if(_action == 'edit') {
                    this.location.href = "edit?tab=metadata&id="+tree.getFolder();
                } else if(_action == 'delete') {
                    /*if('"""+currentdir.type+"""'=='collections' || '"""+currentdir.type+"""'=='root' || '"""+currentdir.type+"""'=='home'){
                        alert('"""+t(lang(req), "delete_root_error_msg")+"""');
                        return 0;
                    }*/
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
                        this.content.location.href = "edit_content?ids="+ids+"&src="+src+"&tab=metadata";
                        r = ""+Math.random()*10000;
                        this.buttons.location.href = "edit_buttons?ids="+ids+"&r="+r;
                    }
                    return 0;
                } else if(_action == "editsingle") {
                    var ids = content.getAllObjectsString();
                    if(ids == '') {
                        reloadPage(tree.getFolder(),'');
                    } else {
                        this.content.location.href = "edit_content?ids="+content.getFirstObject()+"&nodelist="+ids+"&tab=metadata";
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
            if item==tab or tab.startswith(item) or item.startswith(tab):
                return [menuitem.getName(),"*"+ item]
    return [tab]

def filterMenu(menuitems, user):
    hide = users.getHideMenusForUser(user)
    ret = []
    for menu in parseMenuString(menuitems):
        i = []
        for item in menu.getItemList():
            if item not in hide:    
                i.append(item)
            else:
                print "hide editor menu:", item
        menu.item = i
        ret.append(menu)
        
    return ret
    
def handletabs(req, ids, tabs):
    user = users.getUserFromRequest(req)

    n = tree.getNode(ids[0])
    if n.type=="workflows":
        n = tree.getRoot()
    
    menu = filterMenu(getEditMenuString(n.getContentType()), user)
    
    spc = [Menu("sub_header_frontend", "../", target="_parent")]  
    if user.isAdmin():
        spc.append(Menu("sub_header_administration", "../admin", target="_parent"))
        
    if user.isWorkflowEditor():
        spc.append(Menu("sub_header_workflow", "../publish", target="_parent"))

    spc.append(Menu("sub_header_logout", "../logout", target="_parent"))

    return req.getTAL("web/edit/edit.html", {"user":user, "ids":ids, "idstr":",".join(ids), "menu":menu, "breadcrumbs":getBreadcrumbs(menu, req.params.get("tab", tabs)), "spc":spc}, macro="edit_tabs")

    
def error(req):
    req.writeTAL("<tal:block tal:replace=\"errormsg\"/>",{"errormsg":req.params.get("errmsg","")} , macro="edit_errorpage")
    return athana.HTTP_OK
    
    
# delivers all edit modules
editModules = {} 
def getEditModules(force=0):
    if len(editModules)==0:
        path = os.walk(os.path.join(config.basedir, 'web/edit/modules'))
        for root, dirs, files in path:
            for name in [f for f in files if f.endswith(".py") and f!="__init__.py"]:
                try:
                    m = __import__("web.edit.modules." + name[:-3])
                    m = eval("m.edit.modules."+name[:-3])
                    editModules[name[:-3]] = m
                except SyntaxError:
                    logger.error("syntax error in module "+name[:-3])
                except:
                    logger.error("error in module "+name[:-3])
             
        # test for external modules by plugin
        for k,v in config.getsubset("plugins").items():
            path,module = splitpath(v)
            try:
                sys.path += [path+".editmodules"]
                
                for root, dirs, files in os.walk(os.path.join(config.basedir, v+"/editmodules")):
                    for name in [f for f in files if f.endswith(".py") and f!="__init__.py"]:
                        m = __import__(module+".editmodules."+name[:-3])
                        m = eval("m.editmodules."+name[:-3])
                        editModules[name[:-3]] = m
            except ImportError:
                pass # no edit modules in plugin

    return editModules


    
def getIDs(req):
    # update nodelist, if necessary
    if "nodelist" in req.params:
        nodelist = []
        for id in req.params["nodelist"].split(","):
            nodelist.append(tree.getNode(id))
        req.session["nodelist"] = EditorNodeList(nodelist)

    # look for one "id" parameter, containing an id or a list of ids
    id = req.params.get("id")

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

    
def getEditMenuString(ntype, default=0):
    menu_str = ""
    
    for dtype in loadAllDatatypes(): # all known datatypes
        if dtype.name==ntype:
            n = tree.Node("", type=dtype.name)
            
            menu_str = getRoot().get("edit.menu."+dtype.name)
            if (menu_str=="" or default==1) and hasattr(n, "getEditMenuTabs"):
                menu_str = n.getEditMenuTabs()
            break
    return menu_str  
    
def action(req):
    global editModules
    access = AccessData(req)
    user = users.getUserFromRequest(req)
    trashdir = getTrashDir(user)

    if not access.user.isEditor():
        req.write("""permission denied""")
        return
        
    if "tab" in req.params:
        tab = req.params.get("tab").split("_")[-1]
        return editModules[tab].getContent(req, [req.params.get("id")])
    
    srcid = req.params.get("src")
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

    if newfolder!="":
        node = tree.getNode(srcid)
        if not access.hasWriteAccess(node):
            req.writeTAL("web/edit/edit.html", {"id":node.id, "operation":"error"}, macro="newfolder")
            return

        if node.type=="collections":
            # always create a collection in the uppermost hierarchy- independent on
            # what the user requested
            newnode = node.addChild(tree.Node(name=newfolder, type="collection"))
        else:
            if is_collection:
                if node.type!="collection" and node.type!="collections":
                    req.writeTAL("web/edit/edit.html", {"errormsg":"can't create a collection below a node of type "+str(node.type)}, macro="edit_errorpage")
                    return
                newnode = node.addChild(tree.Node(name=newfolder, type="collection"))
            else:
                newnode = node.addChild(tree.Node(name=newfolder, type="directory"))
        
        newnode.set("creator", user.getName())
        newnode.set("creationtime",  str(time.strftime( '%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
        req.writeTAL("web/edit/edit.html", {"id":newnode.id, "operation":"new"}, macro="newfolder")
        return

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
    mysrc = None
    errorobj = None
    try:
        if action=="clear_trash":
            for n in trashdir.getChildren():
                for f in n.getFiles():
                    if os.path.exists(f.retrieveFile()):
                        os.remove(f.retrieveFile())
                trashdir.removeChild(n)
            logger.info(user.getName()+" cleared trash folder with id "+str(trashdir.id))

        for id in idlist:
            obj = tree.getNode(id)
            mysrc = src
            if isDirectory(obj):
                mysrc = obj.getParents()[0]

            if action=="delete":
                if access.hasWriteAccess(mysrc) and access.hasWriteAccess(obj):
                    if mysrc.id!=trashdir.id:
                        mysrc.removeChild(obj)
                        trashdir.addChild(obj)
                        logger.info(user.getName()+" removed "+obj.id+" from "+mysrc.id)
                else:
                    logger.error(user.getName()+" has no write access for node "+mysrc.id)
            
            elif action=="move":
                if dest != mysrc and \
                   access.hasWriteAccess(mysrc) and \
                   access.hasWriteAccess(dest) and \
                   access.hasWriteAccess(obj) and \
                   isDirectory(dest):
                    if not nodeIsChildOfNode(dest,obj):
                        mysrc.removeChild(obj)
                        dest.addChild(obj)
                    else:
                        logger.error(user.getName()+" could not move "+obj.id+" from "+mysrc.id+" to "+dest.id)
                mysrc = None
           
            elif action=="copy":
                if dest != mysrc and \
                   access.hasReadAccess(mysrc) and \
                   access.hasWriteAccess(dest) and \
                   access.hasWriteAccess(obj) and \
                   isDirectory(dest):
                    if not nodeIsChildOfNode(dest,obj):
                        dest.addChild(obj)
                        logger.info(user.getName()+" copied "+obj.id+" from "+mysrc.id+" to "+dest.id)
                    else:
                        logger.error(user.getName()+" could not copy "+obj.id+" from "+mysrc.id+" to "+dest.id)
                mysrc = None
        if not mysrc:
            mysrc = src
    except:
        errorobj = sys.exc_info()
    
    v = {}
    v["action"] = action
    v["mysrcid"] = mysrc.id
    v["srcid"] = srcid
    v["error"] = errorobj
    req.writeTAL("web/edit/edit.html", v, macro="edit_action")


def isDirectory(node):
    return node.type=="directory" or node.type=="root" or node.type=="collection" or node.type=="collections"

def showPaging(req, tab, ids):
    nodelist = req.session.get("nodelist", None)
    nextid = previd = None
    position = absitems = '&nbsp;'
    combodata = ""
    script = ""
    combo = '&nbsp;'
    if nodelist and len(ids)==1:
        previd = nodelist.getPrevious(ids[0])
        nextid = nodelist.getNext(ids[0])
        position, absitems = nodelist.getPositionString(ids[0])
        combodata, script = nodelist.getPositionCombo(tab)

    return req.getTAL("web/edit/edit.html", {"nextid":nextid, "previd":previd, "position":position, "absitems":absitems, "tab":tab,"combodata":combodata, "script":script, "nodeid":ids[0]}, macro="edit_paging")
        
   
def content(req):
    content = {}
    content["script"] = ""
    content["body"] = ""
    v = {}
    v["dircontent"] = ""
    
    path = req.path[1:].split("/")
    if len(path)>=4:
        req.params["style"] = "popup"
        req.params["id"] = path[1]
        req.params["tab"] = path[2]
        req.params["option"] = path[3]
        
    getEditModules()

    access = AccessData(req)
    if not access.user.isEditor():
        return req.writeTAL("web/edit/edit.html", {}, macro="error")

    # remove all caches for the frontend area- we might make changes there
    for sessionkey in ["contentarea", "navframe"]:
        try:
            del req.session[sessionkey]
        except:
            pass

    ids = getIDs(req)
    if req.params.get("type","")=="help" and req.params.get("tab","")=="upload":
        return upload_help(req)

    user = users.getUserFromRequest(req)

    if len(ids)>0:
        node = tree.getNode(ids[0])

    tabs = "content"
    if node.type=="root":
        tabs = "content"
    elif node.id==getUploadDir(user).id:
        tabs = "upload"
    elif node.id==getImportDir(user).id:
        tabs = "imports"
    elif hasattr(node, "getDefaultEditTab"):
        tabs = node.getDefaultEditTab()

    current = req.params.get("tab", tabs)

    # some tabs operate on only one file
    #if current in ["files", "view", "upload"]:
    if current in ["files", "upload"]:
        ids = ids[0:1]

    # display current images
    v["notdirectory"] = 0
    if "image" or "doc" in tree.getNode(ids[0]).getContentType():
        v["notdirectory"] = 1
        items = []
        if current!="view":
            for id in ids:
                node = tree.getNode(id)
                if hasattr(node, "show_node_image"):
                    if not isDirectory(node) and not node.isContainer():
                        items.append(('javascript:fullSizeWindow(\''+id+'\',\''+str(node.get("width"))+'\',\''+str(node.get("height"))+'\')', node.show_node_image()))
                    else:
                        items.append(("",node.show_node_image()))
        v["items"] = items
            
    else: # or current directory
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
        v["dircontent"] = s

    if current=="globals":
        pass

        basedir = config.get("paths.datadir")
            
        file_to_edit = None
        
        if "file_to_edit" in req.params:
            file_to_edit = req.params["file_to_edit"]
            
        if not file_to_edit:
            d = node.getStartpageDict()
            if d and lang(req) in d:
                file_to_edit = d[lang(req)]

        found=False
        for f in node.getFiles():
            if f.mimetype=='text/html':
                filepath = f.retrieveFile().replace(basedir, '')
                if file_to_edit == filepath:
                    found=True
                    result = edit_editor(req, node, f)
                    if result == "error":
                        print "error editing ", f.retrieveFile()
                    break

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
        t = current.split("_")[-1]
        if t in editModules.keys():
            content["body"] += editModules[t].getContent(req, ids) # use standard method of module
        else:
            content["body"] += req.getTAL("web/edit/edit.html",{"module":current}, macro="module_error")
   
    if req.params.get("style","")!="popup": # normal page with header
        v["tabs"] = handletabs(req, ids, tabs)
        v["script"] = content["script"]
        v["body"] = content["body"]
        v["paging"] = showPaging(req, current, ids)
        v["node"] = node       
        req.writeTAL("web/edit/edit.html", v, macro="frame_content")
    
# frame with action drop-downs
def buttons(req):
    node = None
    nodename = ""
    access = AccessData(req)
    
    if "id" in req.params:
        node = tree.getNode(req.params.get("id"))
        
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

    v = {}
    v["iseditor"] = access.user.isEditor()
    v["type"] = dirtype
    v["newdir"] = newdir
    v["newcoll"] = newcoll
    v["name"] = nodename
    
    req.writeTAL("web/edit/edit.html", v, macro="frame_actions")
    
# build browsing tree-frame
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

    def f(req,node,objnum,link,indent,type):
        indent *= 10
        items = ''
        if objnum and node.getType().getName()!="root":
            items = ' ('+str(objnum)+')'

        nodename = node.name
        try: nodename = node.getLabel()
        except: 
            log.logException()

        if isCollection(node):
            cssclass = "coll_"
        else:
            cssclass = "dir_"
        if access.hasWriteAccess(node):
            cssclass += "canwrite"
        else:
            cssclass += "canread"    

        v = {}
        v["id"] = str(node.id)
        v["type"] = type
        v["indent"] = indent
        v["current"] = node.id == currentid
        v["cssclass"] = cssclass
        v["title"] = nodename + ' (ID'+node.id+')'
        v["nodename"] = nodename
        v["items"] = items
        v["link"] = link

        return req.getTAL("web/edit/edit.html", v, macro="build_tree")

    node = tree.getNode(currentid)
    o = None
    if len(node.getParents()):
        o = [node.getParents()[0]]

    home_omitroot = 1
    if len(access.filter(tree.getRoot("home").getChildren())) > 1:
        home_omitroot = 0

    content = ""
    content += writetree(req, tree.getRoot("home"), f, "", openednodes=o, sessionkey="lefttreenodes", omitroot=home_omitroot)
    content += writetree(req, tree.getRoot("collections"), f, "", openednodes=o, sessionkey="lefttreenodes", omitroot=0)
    content += writetree(req, tree.getRoot("navigation"), f, "", openednodes=o, sessionkey="lefttreenodes", omitroot=1)
    
    req.writeTAL("web/edit/edit.html", {"script":"var currentfolder = '"+currentid+"'", "scrollid":scrollid, "content":content}, macro="frame_tree")

