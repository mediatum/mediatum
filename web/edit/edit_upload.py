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
import os
import core.users as users
import core.tree as tree
import re
import utils.date
from utils.log import logException
import core.config as config
import zipfile, PIL.Image
import random 
import logging
from core.datatypes import loadAllDatatypes
from edit_common import *
import utils.date as date
from utils.utils import join_paths, EncryptionException,formatException
from utils.fileutils import importFile

from core.tree import Node
from core.acl import AccessData
from schema.schema import loadTypesFromDB

from core.translation import translate, lang, t

def elemInList(list, name):
    for item in list:
        if item.getName()==name:
            return True
    return False

def edit_upload(req, ids):

    user = users.getUserFromRequest(req)
    uploaddir = tree.getNode(ids[0])

    schemes = AccessData(req).filter(loadTypesFromDB())
    _schemes = []
    for scheme in schemes:
        if scheme.isActive():
            _schemes.append(scheme)
    schemes = _schemes

    # find out which schema allows which datatype, and hence,
    # which overall data types we should display
    dtypes = []
    datatypes = loadAllDatatypes()
    for scheme in schemes:
        for dtype in scheme.getDatatypes():
            if dtype not in dtypes:
                for t in datatypes:
                    if t.getName()==dtype and not elemInList(dtypes, t.getName()):
                        dtypes.append(t)

    #for t in datatypes:
    #    if t.getName() not in dtypes and t.canAlwaysUpload():
    #        dtypes.append(t)
                        
    dtypes.sort(lambda x, y: cmp(translate(x.getLongName(), request=req).lower(),
                                 translate(y.getLongName(), request=req).lower()))

    objtype = ""
    if len(dtypes)==1:
        objtype = dtypes[0]
    else:
        for t in datatypes:
            if t.getName()==req.params.get("objtype",""):
                objtype = t

    # filter schemes for special datatypes
    if req.params.get("objtype","")!="":
        _schemes = []
        for scheme in schemes:
            if req.params.get("objtype","") in scheme.getDatatypes():
                _schemes.append(scheme)
        schemes = _schemes
        schemes.sort(lambda x, y: cmp(translate(x.getLongName(), request=req).lower(),translate(y.getLongName(), request=req).lower()))

    req.write(req.getTAL("web/edit/edit_upload.html",{"id":req.params.get("id"),"datatypes":dtypes, "schemes":schemes, "objtype":objtype, "error":req.params.get("error")},macro="upload_form"))
        
    showdir(req, uploaddir)
    return athana.HTTP_OK


# differs from os.path.split in that it handles windows as well as unix filenames
FNAMESPLIT=re.compile(r'(([^/\\]*[/\\])*)([^/\\]*)')
def mybasename(filename):
    g = FNAMESPLIT.match(filename)
    if g:
        return g.group(3)
    else:
        return filename

def importFileIntoNode(user,realname,tempname,datatype, workflow=0):
    logging.getLogger('usertracing').info(user.name + " upload "+realname+" ("+tempname+")")

    if realname.lower().endswith(".zip"):
        z = zipfile.ZipFile(tempname)
        for f in z.namelist():
            name = mybasename(f)
            if name.startswith("._"):
                # ignore Mac OS X junk
                continue
            rnd = str(random.random())[2:]
            ext = os.path.splitext(name)[1]
            newfilename = join_paths(config.get("paths.tempdir"), rnd+ext)
            fi = open(newfilename, "wb")
            fi.write(z.read(f))
            fi.close()
            importFileIntoNode(user, name, newfilename, datatype)
            os.unlink(newfilename)
        return
    if realname!="":
        n = tree.Node(name=mybasename(realname), type=datatype)
        file = importFile(realname,tempname)
        n.addFile(file)
    else:
        # no filename given
        n = tree.Node(name="", type=datatype)

    # service flags
    n.set("creator", user.getName())
    n.set("creationtime", date.format_date())
    if hasattr(n,"event_files_changed"):
        n.event_files_changed()

    uploaddir = getUploadDir(user)
    uploaddir.addChild(n)

def upload_new(req):
    user = users.getUserFromRequest(req)
    datatype = req.params.get("datatype", "image")
    uploaddir = getUploadDir(user)

    workflow = "" #int(req.params["workflow"])
    
    if "file" in req.params.keys():
        file = req.params["file"]
        del req.params["file"]
        if hasattr(file,"filesize") and file.filesize>0:
            try:
                importFileIntoNode(user, file.filename, file.tempname, datatype, workflow)
                req.request["Location"] = req.makeLink("content", {"id":uploaddir.id})
            except EncryptionException:
                req.request["Location"] = req.makeLink("content", {"id":uploaddir.id, "error":"EncryptionError_"+datatype[:datatype.find("/")]})
            except:
                logException("error during upload")
                req.request["Location"] = req.makeLink("content", {"id":uploaddir.id, "error":"PostprocessingError_"+datatype[:datatype.find("/")]})

            return athana.HTTP_MOVED_TEMPORARILY;

    # upload without file
    importFileIntoNode(user, "", "", datatype, workflow)
    req.request["Location"] = req.makeLink("content", {"id":uploaddir.id})
    return athana.HTTP_MOVED_TEMPORARILY;

    
""" popup with type information"""
def upload_help(req):
    try:
        req.writeTAL("contenttypes/"+req.params.get("objtype", "") +".html", {}, macro="upload_help")
    except:
        None
        
def upload_for_html(req):
    user = users.getUserFromRequest(req)
    datatype = req.params.get("datatype", "image")
    id=(req.path).split('/')[-2]

    n=tree.getNode(id)
    access = AccessData(req)
    if not (access.hasAccess(n,'read') and access.hasAccess(n,'write') and access.hasAccess(n,'data')):
        return 403
    
    for key in req.params.keys():
        if key.startswith("delete_"):
            filename = key[7:-2]
            for file in n.getFiles():
                if file.getName() == filename:
                    n.removeFile(file)

    if "file" in req.params.keys():
        # file upload via (possibly disabled) upload form in custom image browser
        file = req.params["file"]
        del req.params["file"]
        if hasattr(file,"filesize") and file.filesize>0:
            try:
                logging.getLogger('editor').info(user.name + " upload "+file.filename+" ("+file.tempname+")")
                nodefile=importFile(file.filename, file.tempname)
                n.addFile(nodefile)
                req.request["Location"] = req.makeLink("nodefile_browser/%s/" % id, {}) # , {"id":id, "tab":"tab_editor"})
            except EncryptionException:
                req.request["Location"] = req.makeLink("content", {"id":id, "tab":"tab_editor", "error":"EncryptionError_"+datatype[:datatype.find("/")]})
            except:
                logException("error during upload")
                req.request["Location"] = req.makeLink("content", {"id":id, "tab":"tab_editor", "error":"PostprocessingError_"+datatype[:datatype.find("/")]})

            send_nodefile_tal(req)
            return athana.HTTP_OK
        
    if "NewFile" in req.params.keys():
        # file upload via FCKeditor Image Properties / Upload tab
        file = req.params["NewFile"]
        del req.params["NewFile"]
        if hasattr(file,"filesize") and file.filesize>0:
            try:
                logging.getLogger('editor').info(user.name + " upload "+file.filename+" ("+file.tempname+")")
                nodefile=importFile(file.filename, file.tempname)
                n.addFile(nodefile)
            except EncryptionException:
                req.request["Location"] = req.makeLink("content", {"id":id, "tab":"tab_editor", "error":"EncryptionError_"+datatype[:datatype.find("/")]})
            except:
                logException("error during upload")
                req.request["Location"] = req.makeLink("content", {"id":id, "tab":"tab_editor", "error":"PostprocessingError_"+datatype[:datatype.find("/")]})

            originalName=file.filename
            newName=file.tempname.split('/')[2]
            url='/file/'+id+'/'+newName
            
            # the following response is copied from the FCKeditor sources:
            # lib/FCKeditor/files.zip/editor/filemanager/connectors/py/fckoutput.py
            req.write("""<script type="text/javascript">
			(function(){var d=document.domain;while (true){try{var A=window.parent.document.domain;break;}catch(e) {};d=d.replace(/.*?(?:\.|$)/,'');if (d.length==0) break;try{document.domain=d;}catch (e){break;}}})();

			window.parent.OnUploadCompleted(%(errorNumber)s,"%(fileUrl)s","%(fileName)s","%(customMsg)s");
			</script>""" % {
			'errorNumber': 0,
			'fileUrl': url.replace ('"', '\\"'),
			'fileName': originalName.replace ( '"', '\\"' ) ,
			'customMsg': (t(lang(req), "edit_fckeditor_cfm_uploadsuccess")),
			})

            return athana.HTTP_OK

    send_nodefile_tal(req)
    return athana.HTTP_OK
    
def send_fckfile(req, download=0):
    id,filename = (req.path).split("/")[2:4]
    try:
        n = tree.getNode(id)
    except tree.NoSuchNodeError:
        return 404
    access = AccessData(req)
    if not (access.hasAccess(n,'read') and access.hasAccess(n,'data')):
        return 403
    if not access.hasAccess(n,"write") and n.type not in ["directory","collections","collection"]:
        return 403
    file = None
    # try full filename
    for f in n.getFiles():
        if f.getName() == filename:
            file = f
            break

    if file and not os.path.isfile(file.retrieveFile()) and n.get("archive_type")!="":
        archivemanager.getManager(n.get("archive_type")).getArchivedFile(id)

    if not file:
        print "Document",req.path,"not found"
        return 404

    if req.params.get("delete", "") == "True":
        user = users.getUserFromRequest(req)
        logging.getLogger('editor').info(user.name + " going to remove "+file.retrieveFile()+" via startpage editor on node " + id)
        n.removeFile(file)
        try:
            os.remove(file.retrieveFile())
        except:
            logException("could not remove file: %s" % file.retrieveFile())
        return

    return req.sendFile(file.retrieveFile(), file.getMimeType())

def send_nodefile_tal(req):
    
    id=(req.path).split('/')[-2]
    n = tree.getNode(id)
    access = AccessData(req)

    if not (access.hasAccess(n,'read') and access.hasAccess(n,'write') and access.hasAccess(n,'data')):
        return 403
    try:
        node = tree.getNode(id)
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(node,"write") and node.type not in ["directory","collections","collection"]:
        return 403
    
    def fit(imagefile, cn):
        # fits the image into a box with dimensions cn, returning new width and height
        sz=PIL.Image.open(imagefile).size
        (x, y)=(sz[0], sz[1])
        if x > cn[0]:
            y=(y*cn[0])/x
            x=(x*cn[0])/x
        if y > cn[1]:
            x=(x*cn[1])/y
            y=(y*cn[1])/y
        return (x,y)
    
    # only pass images to the file browser
    files = [f for f in node.getFiles() if f.mimetype.startswith("image")]

    # this flag may switch the display of a "delete" button in the customs file browser in web/edit_editor.html
    showdelbutton=True
   
    req.writeTAL("web/edit/edit_editor.html", {"id":id, "node":node, "files":files, "fit":fit, "logoname":node.get("system.logo"), "delbutton":showdelbutton}, macro="fckeditor_customs_filemanager")
    
    return athana.HTTP_OK

