"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>

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

import json

import core.tree as tree
import core.acl as acl
from web.edit.edit_common import showdir, showoperations
from utils.utils import dec_entry_log
from core.translation import translate, lang, t
from core.datatypes import loadAllDatatypes
from schema.schema import loadTypesFromDB


def elemInList(elemlist, name):
    for item in elemlist:
        if item.getName() == name:
            return True
    return False
    

@dec_entry_log
def getContent(req, ids):

    class SortChoice:
        def __init__(self, label, value):
            self.label = label
            self.value = value
    
    def getSchemes(_req):
        return filter(lambda x: x.isActive(), acl.AccessData(_req).filter(loadTypesFromDB()))

    def getDatatypes(_req, _schemes):
        _dtypes = []
        datatypes = loadAllDatatypes()
        for scheme in _schemes:
            for dtype in scheme.getDatatypes():
                if dtype not in _dtypes:
                    for _t in datatypes:
                        if _t.getName() == dtype and not elemInList(dtypes, _t.getName()):
                            dtypes.append(_t)
        _dtypes.sort(lambda x, y: cmp(translate(x.getLongName(), request=_req).lower(), translate(y.getLongName(), request=req).lower()))
        return _dtypes
    
    node = tree.getNode(ids[0])
    
    if "action" in req.params:
        if req.params.get('action') == "resort":
            _dir = "up"
            field = req.params.get('value', '').strip()
            nl = list(node.getChildren())
            if field:
                if field[0] == "-":
                    field = field[1:]
                    _dir = "down"
                nl.sort(lambda x, y: cmp(x.get(field).lower(), y.get(field).lower()))
                if _dir == "down":
                    nl.reverse()
            req.write(json.dumps({'state': 'ok', 'values': showdir(req, node, nodes=nl, sortfield_from_req=field)}))
            return None
        
        elif req.params.get('action') == "save":  # save selection for collection
            field = req.params.get('value')
            if field.strip() == "":
                node.removeAttribute('sortfield')
            else:
                node.set('sortfield', field)
            req.write(json.dumps({'state': 'ok', 'message': translate('edit_content_save_order', request=req)}))
        return None
    
    if node.isContainer():
        schemes = []
        dtypes = []

        v = {"operations": showoperations(req, node), "items": showdir(req, node)}
        access = acl.AccessData(req)
        if access.hasWriteAccess(node):
            schemes = getSchemes(req)
            dtypes = getDatatypes(req, schemes)

        col = node
        if "globalsort" in req.params:
            col.set("sortfield", req.params.get("globalsort"))
        v['collection_sortfield'] = col.get("sortfield")
        sortfields = [SortChoice(t(req, "off"), "")]
        if col.type not in ["root", "collections", "home"]:
            try:
                for ntype, num in col.getAllOccurences(acl.AccessData(req)).items():
                    if ntype.getSortFields():
                        for sortfield in ntype.getSortFields():
                            sortfields += [SortChoice(sortfield.getLabel(), sortfield.getName())]
                            sortfields += [SortChoice(sortfield.getLabel() + t(req, "descending"), "-" + sortfield.getName())]
                        break
            except TypeError:
                pass
        v['sortchoices'] = sortfields
        v['types'] = dtypes
        v['schemes'] = schemes
        v['id'] = ids[0]
        v['count'] = len(node.getContentChildren())
        v['language'] = lang(req)
        v['t'] = t
        return req.getTAL("web/edit/modules/content.html", v, macro="edit_content")    
    if hasattr(node, "editContentDefault"):
        return node.editContentDefault(req)
    return ""