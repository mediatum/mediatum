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
import re
import core.tree as tree
import core.users as users
import logging

from core.acl import AccessData
from core.translation import translate, getDefaultLanguage, t, lang
from utils.log import logException
from utils.utils import isDirectory, isCollection, EncryptionException
from utils.fileutils import importFile


class NodeWrapper:
    def __init__(self, node, nodenumber):
        self.node = node
        self.nodenumber = nodenumber
    
    def getNode():
        return self.node
    
    def getNodeNumber():
        return self.nodenumber

        
class EditorNodeList:
    def __init__(self, nodes):
        self.nodeids = []
        self.nodeid2pos = {}
        i = 0
        for node in nodes:
            if not node.isContainer():
                self.nodeids.append(node.id)
                self.nodeid2pos[node.id] = i
                i += 1
             
    def getNext(self, nodeid):
        try:
            pos = self.nodeid2pos[nodeid] 
        except KeyError:
            return None
        if pos>=len(self.nodeids)-1:
            return None
        return self.nodeids[pos+1]
        
    def getPrevious(self, nodeid): 
        try:
            pos = self.nodeid2pos[nodeid] 
        except KeyError:
            return None
        if pos<=0:
            return None
        return self.nodeids[pos-1]
        
    def getPositionString(self, nodeid):
        try:
            pos = self.nodeid2pos[nodeid] 
        except KeyError:
            return "", ""
        return pos+1, len(self.nodeids)

    def getPositionCombo(self, tab):
        script = """<script language="javascript">
        function gotoContent(cid, tab) {
          window.location.assign('/edit/edit_content?id='+cid+'&tab='+tab);
        }
        </script>"""
        data = []
        for nid in self.nodeids:
            data.append((nid, len(data)+1))
        return data, script
        

def existsHomeDir(user):
    username = user.getName()
    userdir = None
    for c in tree.getRoot("home").getChildren():
        if (c.getAccess("read") or "").find("{user "+username+"}")>=0 and (c.getAccess("write") or "").find("{user "+username+"}")>=0:
            userdir = c
    return (not userdir==None)

def getHomeDir(user):
    username = user.getName()
    userdir = None
    for c in tree.getRoot("home").getChildren():
        if (c.getAccess("read") or "").find("{user "+username+"}")>=0 and (c.getAccess("write") or "").find("{user "+username+"}")>=0:
            userdir = c
    if not userdir:
        userdir = tree.getRoot("home").addChild(tree.Node(name=translate("user_directory", getDefaultLanguage())+" ("+username+")", type="directory"))
        userdir.setAccess("read","{user "+username+"}")
        userdir.setAccess("write","{user "+username+"}")
        userdir.setAccess("data","{user "+username+"}")
        
        # re-sort home dirs alphabetically
        i = 0
        for child in tree.getRoot("home").getChildren().sort("name"):
            child.setOrderPos(i)
            i += 1
    return userdir
 
def renameHomeDir(user, newusername):
    if (existsHomeDir(user)):
        getHomeDir(user).setName(translate("user_directory", getDefaultLanguage())+" ("+newusername+")")

        
def getUploadDir(user):
    userdir = getHomeDir(user)
    uploaddir = None
    for c in userdir.getChildren():
        if c.name==translate("user_upload", getDefaultLanguage()):
            uploaddir = c
    if not uploaddir:
        uploaddir = userdir.addChild(tree.Node(name=translate("user_upload", getDefaultLanguage()), type="directory"))
    return uploaddir

def getImportDir(user):
    userdir = getHomeDir(user)
    importdir = None
    for c in userdir.getChildren():
        if c.name==translate("user_import", getDefaultLanguage()):
            importdir = c
    if not importdir:
        importdir = userdir.addChild(tree.Node(name=translate("user_import", getDefaultLanguage()), type="directory"))
    return importdir

def getFaultyDir(user):
    userdir = getHomeDir(user)
    faultydir = None
    for c in userdir.getChildren():
        if c.name==translate("user_faulty", getDefaultLanguage()):
            faultydir = c
    if not faultydir:
        faultydir = userdir.addChild(tree.Node(name=translate("user_faulty", getDefaultLanguage()), type="directory"))
    return faultydir

def getTrashDir(user):
    userdir = getHomeDir(user)
    trashdir = None
    for c in userdir.getChildren():
        if c.name==translate("user_trash", getDefaultLanguage()):
            trashdir = c
    if not trashdir:
        trashdir = userdir.addChild(tree.Node(name=translate("user_trash", getDefaultLanguage()), type="directory"))
    return trashdir

def showdir(req, node, publishwarn="auto", markunpublished=0):
    if publishwarn=="auto":
        user = users.getUserFromRequest(req)
        homedir = getHomeDir(user)
        homedirs = getAllSubDirs(homedir)
        publishwarn = node in homedirs
    return shownodelist(req,node.getChildren(), publishwarn=publishwarn, markunpublished=markunpublished, dir=node)

def getAllSubDirs(node):
    dirs = []
    for c in node.getChildren():
        if c.type=="directory":
            dirs += [c] + getAllSubDirs(c)
    return dirs
            

def shownodelist(req, nodes, publishwarn=1, markunpublished=0, dir=None):
    req.session["nodelist"] = EditorNodeList(nodes)
    script_array = "allobjects = new Array();\n"
    nodelist = []
        
    user = users.getUserFromRequest(req)

    for child in nodes:
        if isDirectory(child) or isCollection(child):
            continue
        script_array += "allobjects['"+child.id+"'] = 0;\n"
        nodelist.append(child)

    chkjavascript = ""
    notpublished = {}
    if publishwarn or markunpublished:
        homedir = getHomeDir(user)
        homedirs = getAllSubDirs(homedir)
        if markunpublished:
            chkjavascript = """<script language="javascript">"""
        for node in nodes:
            ok = 0
            for p in node.getParents():
                if p not in homedirs:
                    ok = 1
            if not ok:
                if markunpublished:
                    chkjavascript += """allobjects['check%s'] = 1;
                                        document.getElementById('check%s').checked = true;
                                     """ % (node.id,node.id)

                notpublished[node] = node
        chkjavascript += """</script>"""
        # if all nodes are properly published, don't bother
        # to warn the user
        if not notpublished:
            publishwarn = 0

    unpublishedlink = None
    if publishwarn:
        user = users.getUserFromRequest(req)
        if dir:
            uploaddir = dir
        else:
            uploaddir = getUploadDir(user)
        unpublishedlink = "edit?tab=publish&id="""+uploaddir.id;

    return req.getTAL("web/edit/edit_common.html", {"notpublished": notpublished, "chkjavascript": chkjavascript, "unpublishedlink": unpublishedlink, "nodelist":nodelist, "script_array":script_array}, macro="show_nodelist")


def isUnFolded(unfoldedids, id):
    try:
        return unfoldedids[id]
    except:
        unfoldedids[id] = 0
        return 0

def writenode(req, node, unfoldedids, f, indent, key, access, ret=""):
    if node.type not in ["directory", "collection", "root", "home", "collections","navigation"] and not node.type.startswith("directory"):
        return ret
    if not access.hasReadAccess(node):
        return ret

    isunfolded = isUnFolded(unfoldedids, node.id)

    num = 0
    objnum = 0
    for c in node.getChildren():
        if c.type in["directory", "collection"] or c.type.startswith("directory"):
            num += 1
        else:
            objnum += 1

    if num:
        if isunfolded:
            ret+=f(req, node, objnum, "edit_tree?tree_fold="+node.id, indent, type=1)
        else:
            ret+=f(req, node, objnum, "edit_tree?tree_unfold="+node.id, indent, type=2)
    else:
        ret+=f(req, node, objnum, "", indent, type=3)

    if isunfolded:
        for c in node.getChildren().sort():
            ret+= writenode(req, c, unfoldedids, f, indent+1, key, access)
    return ret

def writetree(req, node, f, key="", openednodes=None, sessionkey="unfoldedids", omitroot=0):
    ret = ""
    access = AccessData(req)

    try:
        unfoldedids = req.session[sessionkey]
        len(unfoldedids)
    except:
        req.session[sessionkey] = unfoldedids = {tree.getRoot().id : 1}

    if openednodes:
        # open all selected nodes and their parent nodes
        def o(u,n):
            u[n.id] = 1
            for n in n.getParents():
                o(u,n)
        for n in openednodes:
            o(unfoldedids, n)
        req.session[sessionkey] = unfoldedids

    try:
        unfold = req.params["tree_unfold"]
        unfoldedids[unfold] = 1
    except KeyError:
        pass
    
    try:
        fold = req.params["tree_fold"]
        unfoldedids[fold] = 0
    except KeyError:
        pass
   
    if omitroot:
        for c in node.getChildren().sort("name"):
            ret += writenode(req, c, unfoldedids, f, 0, key, access)
    else:
        ret += writenode(req, node, unfoldedids, f, 0, key, access)

    return ret
    
def upload_help(req):
    try:
        return req.writeTAL("contenttypes/"+req.params.get("objtype", "") +".html", {}, macro="upload_help")
    except:
        None
        
def send_nodefile_tal(req):
    if "file" in req.params:
        return upload_for_html(req)
    
    id = req.params.get("id")
    node = tree.getNode(id)
    access = AccessData(req)

    if not (access.hasAccess(node,'read') and access.hasAccess(node,'write') and access.hasAccess(node,'data') and node.type in ["directory","collections","collection"]) :
        return ""
    
    def fit(imagefile, cn):
        # fits the image into a box with dimensions cn, returning new width and height
        try:
            sz = PIL.Image.open(imagefile).size
            (x, y)=(sz[0], sz[1])
            if x > cn[0]:
                y = (y*cn[0])/x
                x = (x*cn[0])/x
            if y > cn[1]:
                x = (x*cn[1])/y
                y = (y*cn[1])/y
            return (x,y)
        except:
            return cn
    
    # only pass images to the file browser
    files = [f for f in node.getFiles() if f.mimetype.startswith("image")]

    # this flag may switch the display of a "delete" button in the customs file browser in web/edit/modules/startpages.html
    showdelbutton = True
    return req.getTAL("web/edit/modules/startpages.html", {"id":id, "node":node, "files":files, "fit":fit, "logoname":node.get("system.logo"), "delbutton":True}, macro="fckeditor_customs_filemanager")
        
def upload_for_html(req):
    user = users.getUserFromRequest(req)
    datatype = req.params.get("datatype", "image")
    
    id = req.params.get("id")
    node = tree.getNode(id)

    access = AccessData(req)
    if not (access.hasAccess(node,'read') and access.hasAccess(node,'write') and access.hasAccess(node,'data')):
        return 403
    
    for key in req.params.keys():
        if key.startswith("delete_"):
            filename = key[7:-2]
            for file in n.getFiles():
                if file.getName()==filename:
                    n.removeFile(file)

    if "file" in req.params.keys():
        # file upload via (possibly disabled) upload form in custom image browser
        file = req.params["file"]
        del req.params["file"]
        if hasattr(file,"filesize") and file.filesize>0:
            try:
                logging.getLogger('editor').info(user.name + " upload "+file.filename+" ("+file.tempname+")")
                nodefile = importFile(file.filename, file.tempname)
                node.addFile(nodefile)
                req.request["Location"] = req.makeLink("nodefile_browser/%s/" % id, {})
            except EncryptionException:
                req.request["Location"] = req.makeLink("content", {"id":id, "tab":"tab_editor", "error":"EncryptionError_"+datatype[:datatype.find("/")]})
            except:
                logException("error during upload")
                req.request["Location"] = req.makeLink("content", {"id":id, "tab":"tab_editor", "error":"PostprocessingError_"+datatype[:datatype.find("/")]})
            return send_nodefile_tal(req)
        
    if "NewFile" in req.params.keys():
        # file upload via FCKeditor Image Properties / Upload tab
        file = req.params["NewFile"]
        del req.params["NewFile"]
        if hasattr(file,"filesize") and file.filesize>0:
            try:
                logging.getLogger('editor').info(user.name + " upload "+file.filename+" ("+file.tempname+")")
                nodefile = importFile(file.filename, file.tempname)
                node.addFile(nodefile)
            except EncryptionException:
                req.request["Location"] = req.makeLink("content", {"id":id, "tab":"tab_editor", "error":"EncryptionError_"+datatype[:datatype.find("/")]})
            except:
                logException("error during upload")
                req.request["Location"] = req.makeLink("content", {"id":id, "tab":"tab_editor", "error":"PostprocessingError_"+datatype[:datatype.find("/")]})

            originalName = file.filename

            url = '/file/'+id+'/'+file.tempname.split('/')[-1]
            
            # the following response is copied from the FCKeditor sources:
            # lib/FCKeditor/files.zip/editor/filemanager/connectors/py/fckoutput.py
            return """<script type="text/javascript">
            (function(){var d=document.domain;while (true){try{var A=window.parent.document.domain;break;}catch(e) {};d=d.replace(/.*?(?:\.|$)/,'');if (d.length==0) break;try{document.domain=d;}catch (e){break;}}})();

            window.parent.OnUploadCompleted(%(errorNumber)s,"%(fileUrl)s","%(fileName)s","%(customMsg)s");
            </script>""" % {
            'errorNumber': 0,
            'fileUrl': url.replace ('"', '\\"'),
            'fileName': originalName.replace ( '"', '\\"' ) ,
            'customMsg': (t(lang(req), "edit_fckeditor_cfm_uploadsuccess")),
            }

    return send_nodefile_tal(req)

