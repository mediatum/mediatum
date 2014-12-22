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
import logging

import core.users as users
import core.tree as tree
import core.acl as acl
import schema.bibtex as bibtex
import schema.citeproc as citeproc
import schema.importbase as importbase

from utils.utils import dec_entry_log
from web.edit.edit_common import showdir
from core.translation import lang, t
from core.acl import AccessData
from core.transition import httpstatus

logg = logging.getLogger("editor")


def getInformation():
    return {"version":"1.0", "system":1}


@dec_entry_log
def getContent(req, ids):
    user = users.getUserFromRequest(req)
    access = AccessData(user=user)
    language = lang(req)
    node = tree.getNode(ids[0])

    if not access.hasWriteAccess(node):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if req.params.get("upload")=="uploadfile":
        # try to import file
        return import_new(req)


    v = {"error":req.params.get("error")}

    class SortChoice:
        def __init__(self, label, value):
            self.label = label
            self.value = value

    col = node
    if "globalsort" in req.params:
        col.set("sortfield", req.params.get("globalsort"))
    v['collection_sortfield'] = col.get("sortfield")
    sortfields = [SortChoice(t(req,"off"),"")]
    if col.type not in ["root", "collections", "home"]:
        for ntype, num in col.getAllOccurences(acl.AccessData(req)).items():
            if ntype.getSortFields():
                for sortfield in ntype.getSortFields():
                    sortfields += [SortChoice(sortfield.getLabel(), sortfield.getName())]
                    sortfields += [SortChoice(sortfield.getLabel()+t(req,"descending"), "-"+sortfield.getName())]
                break
    v['sortchoices'] = sortfields
    v['ids'] = ids
    v['count'] = len(node.getContentChildren())
    v['nodelist'] = showdir(req, node)
    v['language'] = lang(req)
    v['t'] = t

    _html = req.getTAL("web/edit/modules/imports.html", v, macro="upload_form")

    return _html


@dec_entry_log
def import_new(req):
    reload(bibtex)
    user = users.getUserFromRequest(req)
    importdir= users.getImportDir(user)
    del req.params["upload"]

    if "file" in req.params and req.params["doi"]:
        req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":"doi_and_bibtex_given"})
        req.params["error"] = "doi_and_bibtex_given"

        msg_t = (user.getName(), importdir.id, importdir.name, importdir.type, req.params["error"])
        msg = "%s using import module for node %r (%r, %r): Error: %r" % msg_t
        logg.info(msg)

    elif "file" in req.params.keys():
        file = req.params["file"]
        del req.params["file"]
        if hasattr(file,"filesize") and file.filesize>0:
            try:
                bibtex.importBibTeX(file.tempname, importdir, req)
                req.request["Location"] = req.makeLink("content", {"id":importdir.id})
            except ValueError, e:
                req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":str(e)})
                req.params["error"] = str(e)
            except bibtex.MissingMapping,e:
                req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":str(e)})
                req.params["error"] = str(e)
            except:
                logg.exception("exception in import_new")
                req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":"PostprocessingError"})
                req.params["error"] = "file_processingerror"
            msg_t = (user.getName(), importdir.id, importdir.name, importdir.type, req.params)
            msg = "%s used import module for bibtex import for node %r (%r, %r): %r" % msg_t
            logg.info(msg)
            return getContent(req, [importdir.id])

    elif req.params["doi"]:
        doi = req.params["doi"]
        logg.info("processing DOI import for: %s", doi)
        try:
            doi_extracted = citeproc.extract_and_check_doi(doi)
            citeproc.import_doi(doi_extracted, importdir)
        except citeproc.InvalidDOI:
            logg.error("Invalid DOI: '%s'", doi)
            req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":"doi_invalid"})
            req.params["error"] = "doi_invalid"
        except citeproc.DOINotFound:
            logg.error("DOI not found: '%s'", doi)
            req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":"doi_unknown"})
            req.params["error"] = "doi_unknown"
        except importbase.NoMappingFound as e:
            logg.error("no mapping found for DOI: '%s', type '%s'", doi, e.typ)
            req.request["Location"] = req.makeLink("content", {"id":importdir.id, "error":"doi_type_not_mapped"})
            req.params["error"] = "doi_type_not_mapped"
        else:
            req.request["Location"] = req.makeLink("content", {"id":importdir.id})
        msg_t = (user.getName(), importdir.id, importdir.name, importdir.type, req.params)
        msg = "%s used import module for doi import for node %r (%r, %r): %r" % msg_t
        logg.info(msg)
    else:
        # error while import, nothing given
        req.params["error"] = "edit_import_nothing"
        msg_t = (user.getName(), importdir.id, importdir.name, importdir.type, req.params)
        msg = "%s used import module but did not specify import source for node %r (%r, %r): %r" % msg_t
        logg.info(msg)

    return getContent(req, [importdir.id])
