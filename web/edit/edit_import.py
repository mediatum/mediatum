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
import zipfile
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
from schema.bibtex import importBibTeX,MissingMapping

from core.translation import translate, lang, t

def edit_import(req, ids):

    user = users.getUserFromRequest(req)
    importdir = tree.getNode(ids[0])

    req.write(req.getTAL("web/edit/edit_import.html",{"error":req.params.get("error")},macro="upload_form"))
    
    showdir(req, importdir)
    return athana.HTTP_OK

def import_new(req):
    user = users.getUserFromRequest(req)
    importdir= getImportDir(user)
    
    if "file" in req.params.keys():
        file = req.params["file"]
        del req.params["file"]
        if hasattr(file,"filesize") and file.filesize>0:
            try:
                importBibTeX(file.tempname, importdir)
                req.request["Location"] = req.makeLink("content", {"id":importdir.id})
            except MissingMapping,e:
                req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":str(e)})
            except:
                logException("error during upload")
                req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":"PostprocessingError"})

            return athana.HTTP_MOVED_TEMPORARILY;

    req.params["error"] = t(req, "no file selected")
    return edit_import(req, [importdir.id])

