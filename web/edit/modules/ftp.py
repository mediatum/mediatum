"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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
import logging
import os

import core.config as config

from schema.schema import get_permitted_schemas
from core.translation import translate
from core.transition import httpstatus, current_user
from core import Node
from core import db

q = db.query
logg = logging.getLogger(__name__)


def getContent(req, ids):
    user = current_user
    if "ftp" in user.hidden_edit_functions:
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    ids = ids[0] # use only first selected node
    node = q(Node).get(ids)
    error = ""

    def processFile(node, file, ftype):
        nname = file.abspath.split("/")
        nname = "/".join(nname[:-1])+"/"+nname[-1][4:]
        try:
            os.rename(file.abspath, nname)
        except:
            nname = file.abspath
        fnode = Node(nname.split("/")[-1], ftype)
        node.files.remove(file)
        file._path = file._path.replace(config.get("paths.datadir"), "")
        file._path = "/".join(file._path.split("/")[:-1]) + "/"+fnode.name
        fnode.files.append(file)
        file.filetype = fnode.get_upload_filetype()
        fnode.event_files_changed()
        node.children.append(fnode)
        db.session.commit()
        return fnode

    for key in req.params.keys():
        if key.startswith("process|"): # process selected file (single)
            fname = key[:-2].split("|")[-1]
            ftype = req.params.get("schema").replace(";","")
            if ftype!="":
                for f in node.files:
                    if f.base_name==fname:
                        processFile(node, f, ftype)
                        break
                break
            else:
                error = "edit_ftp_error1"

        elif key.startswith("del|"):
            for f in node.files:
                if f.base_name==key[4:-2]:
                    node.files.remove(f)
                    break
            break

        elif key.startswith("delall"): # delete all selected files
            delfiles = [f.split("|")[-1] for f in req.params.get("selfiles").split(";")]

            for f in node.files:
                if f.base_name in delfiles:
                    node.files.remove(f)

            break

        elif key.startswith("processall"): # process all selected files
            for file in req.params.get("selfiles", "").split(";"):
                if file:
                    ftype, fname = file.split("|")
                    if "multschema|"+ftype in req.params and req.params.get("multschema|"+ftype)!="":
                        for f in node.files:
                            if f.base_name == fname:
                                logg.info("use %s/%s", ftype, req.params.get("multschema|"+ftype))
                                processFile(node, f, ftype+"/"+req.params.get("multschema|"+ftype) )
                                break
                    else:
                        error = "edit_ftp_error2"
                        break
            break

    files = filter(lambda x: x.base_name.startswith("ftp_"), node.files)
    types = []
    for f in files:
        if f.filetype not in types:
            if f.filetype != "other":
                types.append(f.filetype)

    dtypes = {}
    for scheme in get_permitted_schemas():
        for dtype in scheme.getDatatypes():
            if dtype not in dtypes.keys():
                dtypes[dtype] = []
            if scheme not in dtypes[dtype]:
                dtypes[dtype].append(scheme)

    for t in dtypes:
        dtypes[t].sort(lambda x, y: cmp(translate(x.getLongName(), request=req).lower(), translate(y.getLongName(), request=req).lower()))

    db.session.commit()

    if not node.has_write_access():
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    v = {}
    v['error'] = error
    v['files'] = files
    v['node'] = node
    v['schemes'] = dtypes # schemes
    v['usedtypes'] = types
    v['tab'] = req.params.get("tab", "")
    v['ids'] = ids
    v["script"] = "<script> parent.reloadTree('"+req.params.get("id")+"');</script>"

    return req.getTAL("web/edit/modules/ftp.html", v, macro="edit_ftp")


# used in plugins?
def adduseropts(user):
    ret = []

    dtypes = {}
    for scheme in get_permitted_schemas():
        for dtype in scheme.getDatatypes():
            if dtype not in dtypes.keys():
                dtypes[dtype] = []
            if scheme not in dtypes[dtype]:
                dtypes[dtype].append(scheme)

    i = [x.getLongName() for x in dtypes['image']]
    i.sort()

    field = Node("ftp.type_image", "metafield")
    field.set("label", "ftp_image_schema")
    field.set("type", "list")
    field.set("valuelist", "\r\n".join(i))
    ret.append(field)

    d = [x.getLongName() for x in dtypes['document']]
    d.sort()

    field = Node("ftp.type_document", "metafield")
    field.set("label", "ftp_document_schema")
    field.set("type", "list")
    field.set("valuelist", "\r\n".join(d))
    ret.append(field)

    return ret
