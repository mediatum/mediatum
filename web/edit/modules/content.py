# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import json
import mediatumtal.tal as _tal

import core.translation as _core_translation
import web.common.pagination as _web_common_pagination
import web.edit.edit_common as _web_edit_edit_common
from core import db
from contenttypes import Data, Home, Collection, Collections
from core.systemtypes import Root
from web.edit.edit_common import showoperations, searchbox_navlist_height
from web.frontend.frame import render_edit_search_box
from schema.schema import get_permitted_schemas
from web.edit.edit_common import get_searchparams
import urllib
import web.common.sort as _sort

q = db.query


def elemInList(elemlist, name):
    for item in elemlist:
        if item.getName() == name:
            return True
    return False


def getContent(req, ids):

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
    show_dir_nav = _web_edit_edit_common.ShowDirNav(req, node)

    if "action" in req.params:
        if req.params.get('action') == "resort":
            field = req.params.get('value', '').strip()
            res = show_dir_nav.showdir(sortfield=field)
            res = json.dumps({'state': 'ok', 'values': res}, ensure_ascii=False)
            req.response.set_data(res)
            return None

        elif req.params.get('action') == "save":  # save selection for collection
            field = req.params.get('value')
            if field.strip() == "" or field.strip() == "off":
                if node.get('sortfield'):
                    node.removeAttribute('sortfield')
            else:
                node.set('sortfield', field)
            nodes_per_page = req.params.get('nodes_per_page')
            if nodes_per_page.strip() == "":
                if node.get('nodes_per_page'):
                    node.removeAttribute('nodes_per_page')
            else:
                node.set('nodes_per_page', nodes_per_page)
            req.response.set_data(json.dumps({'state': 'ok'}))

            db.session.commit()
        return None

    if node.isContainer():
        schemes = []
        dtypes = []

        item_count = []

        items = show_dir_nav.showdir(item_count=item_count)
        nav = show_dir_nav.shownav()
        v = {"operations": showoperations(req, node), "items": items, "nav": nav}
        if node.has_write_access():
            schemes = get_permitted_schemas()
            dtypes = getDatatypes(req, schemes)

        if "globalsort" in req.params:
            node.set("sortfield", req.params.get("globalsort"))
        if req.params.get("sortfield", "") != "":
            v['collection_sortfield'] = req.params.get("sortfield")
        else:
            v['collection_sortfield'] = node.get("sortfield")

        if req.values.get("nodes_per_page"):
            v['npp_field'] = req.values["nodes_per_page"]
        else:
            v['npp_field'] = node.get("nodes_per_page")
        if not v['npp_field']:
            v['npp_field'] = _web_common_pagination.get_default_nodes_per_page(True)

        search_html = render_edit_search_box(node, _core_translation.lang(req), req, edit=True)
        searchmode = req.params.get("searchmode")
        navigation_height = searchbox_navlist_height(req, item_count)
        if not isinstance(node, (Root, Collections, Home)):
            sortchoices = _sort.get_sort_choices(
                    container=node,
                    off="off",
                    t_off=_core_translation.t(req, "off"),
                    t_desc=_core_translation.t(req, "descending"),
                )
        else:
            sortchoices = ()

        count = item_count[0] if item_count[0] == item_count[1] else "%d from %d" % (item_count[0], item_count[1])
        v['sortchoices'] = tuple(sortchoices)
        v['types'] = dtypes
        v['schemes'] = schemes
        v['id'] = ids[0]
        v['count'] = count
        v['language'] = _core_translation.lang(req)
        v['search'] = search_html
        v['navigation_height'] = navigation_height
        v['parent'] = node.id
        v['query'] = req.query_string.replace('id=','src=')
        searchparams = get_searchparams(req)
        searchparams = {k: unicode(v).encode("utf8") for k, v in searchparams.items()}
        v['searchparams'] = urllib.urlencode(searchparams)
        v['get_ids_from_query'] = ",".join(show_dir_nav.get_ids_from_req())
        v['edit_all_objects'] = _core_translation.t(_core_translation.lang(req), "edit_all_objects").format(item_count[1])
        v['t'] = t
        res = _tal.processTAL(v, file="web/edit/modules/content.html", macro="edit_content", request=req)
        show_dir_nav.nodes = None
        return res
    if hasattr(node, "editContentDefault"):
        return node.editContentDefault(req)
    return ""
