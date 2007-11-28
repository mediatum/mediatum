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
import core.config as config
import zipfile
import random 
import logging
from core.datatypes import loadAllDatatypes
from edit_common import *
import utils.date as date

from utils.fileutils import importFile

from core.tree import Node
from core.acl import AccessData
from schema.schema import loadTypesFromDB

from core.translation import translate, lang

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
        

    #evalutate datatypes
    dtypes = []
    datatypes = loadAllDatatypes()
    for scheme in schemes:
        for dtype in scheme.getDatatypes():
            if dtype not in dtypes:
                for t in datatypes:
                    if t.getName()==dtype and not elemInList(dtypes, t.getName()):
                        dtypes.append(t)
                        
    dtypes.sort(lambda x, y: cmp(translate(x.getLongName(), request=req).lower(),translate(y.getLongName(), request=req).lower()))

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
        #try:
        n.event_files_changed()
        #except "PostprocessingError":
        #    raise "PostprocessingError"

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
        if file.filesize>0:
            try:
                importFileIntoNode(user, file.filename, file.tempname, datatype, workflow)
                req.request["Location"] = req.makeLink("content", {"id":uploaddir.id})
            except:
                req.request["Location"] = req.makeLink("content", {"id":uploaddir.id, "error":"PostprocessingError_"+datatype[:datatype.find("/")]})

            return athana.HTTP_MOVED_TEMPORARILY;

    # upload without file
    importFileIntoNode(user, "", "", datatype, workflow)
    req.request["Location"] = req.makeLink("content", {"id":uploaddir.id})
    return athana.HTTP_MOVED_TEMPORARILY;

    
""" popup with type information"""
def upload_help(req):
    try:
        req.writeTAL("contenttype/"+req.params.get("objtype", "") +".html", {}, macro="upload_help")
    except:
        None
    
