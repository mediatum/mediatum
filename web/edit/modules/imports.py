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
import zipfile

import core.users as users
import core.tree as tree
import schema.bibtex as bibtex

from utils.fileutils import importFileToRealname
from utils.log import logException
from web.edit.edit_common import showdir
 

def getInformation():
    return {"version":"1.0", "system":1}
    
def getContent(req, ids):   
    if req.params.get("upload")=="uploadfile":
        # try to import tmpfile
        return import_new(req)
    return req.getTAL("web/edit/modules/imports.html",{"error":req.params.get("error")},macro="upload_form") + showdir(req, tree.getNode(ids[0]))

def import_new(req):
    reload(bibtex)
    user = users.getUserFromRequest(req)
    importdir = users.getImportDir(user)
    del req.params["upload"]
    
    if "file" in req.params.keys():
        tmpfile = req.params["file"]
        del req.params["file"]
        if hasattr(tmpfile,"filesize") and tmpfile.filesize>0:
            if zipfile.is_zipfile(tmpfile.tempname):
                with zipfile.ZipFile(tmpfile.tempname, 'r') as zpfile:
                    for fl in zpfile.filelist:
                        if fl.filename.endswith('.bib'):
                            bibfile = zpfile.extract(fl)
                            try:
                                filelist = []
                                for entry in bibtex.getentries(bibfile):
                                    if "originalfilename" in entry[2].keys():
                                        for name in zpfile.namelist():
                                            if name.endswith(entry[2].get("originalfilename")):
                                                source = zpfile.open(name, 'r')
                                                filelist.append(importFileToRealname(name, source.name))
                                                source.close()
                                                break
                                bibtex.importBibTeX(bibfile, importdir, req, originalfiles=filelist)
                                req.request["Location"] = req.makeLink("content", {"id":importdir.id})
                            except ValueError, e:
                                req.params["error"] = str(e)
                            except bibtex.MissingMapping,e:
                                req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":str(e)})
                                req.params["error"] = str(e)
                            except:
                                logException("error during upload")
                                req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":"PostprocessingError"})
                                req.params["error"] = "file_processingerror"
            else:
                try:
                    bibtex.importBibTeX(tmpfile.tempname, importdir, req)
                    req.request["Location"] = req.makeLink("content", {"id":importdir.id})
                except ValueError, e:
                    req.params["error"] = str(e)
                except bibtex.MissingMapping,e:
                    req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":str(e)})
                    req.params["error"] = str(e)
                except:
                    logException("error during upload")
                    req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":"PostprocessingError"})
                    req.params["error"] = "file_processingerror"
                    
            return getContent(req, [importdir.id])
    
    # error while import, no tmpfile given
    req.params["error"] = "no_file_transferred"
    return getContent(req, [importdir.id])
