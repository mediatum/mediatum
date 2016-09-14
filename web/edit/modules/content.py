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

from core import db
from contenttypes import Data, Home, Collections
from core.systemtypes import Root
from web.edit.edit_common import showdir, showoperations
from utils.utils import dec_entry_log
from core.translation import translate, lang, t
from schema.schema import get_permitted_schemas

q = db.query


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

    def getDatatypes(_req, _schemes):
        _dtypes = []
        datatypes = Data.get_all_datatypes()
        for scheme in _schemes:
            for dtype in scheme.getDatatypes():
                if dtype not in _dtypes:
                    for _t in datatypes:
#                         if _t.getName() == dtype and not elemInList(dtypes, _t.getName()):
                        dtypes.append(_t)
        _dtypes.sort(lambda x, y: cmp(translate(x.getLongName(), request=_req).lower(), translate(y.getLongName(), request=req).lower()))
        return _dtypes

    node = q(Data).get(long(ids[0]))

    if "action" in req.params:
        if req.params.get('action') == "resort":
            field = req.params.get('value', '').strip()
            req.write(json.dumps({'state': 'ok', 'values': showdir(req, node, sortfield=field)}, ensure_ascii=False))
            return None

        elif req.params.get('action') == "save":  # save selection for collection
            field = req.params.get('value')
            if field.strip() == "":
                node.removeAttribute('sortfield')
            else:
                node.set('sortfield', field)
            req.write(json.dumps({'state': 'ok'}))
            db.session.commit()
        return None

    if node.isContainer():
        schemes = []
        dtypes = []

        v = {"operations": showoperations(req, node), "items": showdir(req, node)}
        if node.has_write_access():
            schemes = get_permitted_schemas()
            dtypes = getDatatypes(req, schemes)

        col = node
        if "globalsort" in req.params:
            col.set("sortfield", req.params.get("globalsort"))
        v['collection_sortfield'] = col.get("sortfield")
        sort_choices = [SortChoice(t(req, "off"), "")]
        if not isinstance(col, (Root, Collections, Home)):
            for node in col.content_children_for_all_subcontainers: # XXX: now without acl filtering, do we need this?
                sortfields = node.getSortFields()
                if sortfields:
                    for sortfield in sortfields:
                        sort_choices += [SortChoice(sortfield.getLabel(), sortfield.getName())]
                        sort_choices += [SortChoice(sortfield.getLabel() + t(req, "descending"), "-" + sortfield.getName())]
                    break
        v['sortchoices'] = sort_choices
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
