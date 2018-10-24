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
import os as _os
import shutil
import re
import functools as _functools
import itertools as _itertools

from schema.schema import getMetadataType

import sqlalchemy as _sqlalchemy
import backports.functools_lru_cache as _backports_functools_lru_cache

from schema.schema import VIEW_DATA_ONLY, VIEW_HIDE_EMPTY
from core.translation import t, lang
from utils.utils import getCollection
from core import webconfig
from core import db
from core import Node
from contenttypes import Container
from utils.pathutils import getPaths
from utils import userinput
from core import httpstatus
from core.request_handler import sendFile as _sendFile
import core.database.postgres as _database_postgres
import core.database.postgres.node as _database_postgres_node
import utils.utils as _utils_utils
import web.frontend.printview as _web_frontend_printview

#
# execute fullsize method from node-type
#


logg = logging.getLogger(__name__)
q = db.query


def popup_fullsize(req):
    nid = userinput.string_to_int(req.args.get("id", type=int))
    if nid is None:
        req.response.status_code = httpstatus.HTTP_BAD_REQUEST
        req.response.set_data(t(lang(req), "edit_common_noobjectsfound"))
        return
    
    node = q(Node).get(nid)
    if not isinstance(node, Node):
        req.response.status_code = httpstatus.HTTP_NOT_FOUND
        req.response.set_data(t(lang(req), "edit_common_noobjectsfound"))
        return
    
    version_id = req.values.get("v")
    version = node.get_tagged_version(unicode(version_id))
    node_or_version = version if version else node
    if not node_or_version.has_read_access():
        req.response.set_data(t(lang(req), "permission_denied"))
        return httpstatus.HTTP_FORBIDDEN

    return node_or_version.popup_fullsize(req)
#
# execute thumbBig method from node-type
#


def popup_thumbbig(req):
    node = q(Node).get(req.params["id"])
    if not isinstance(node, Node):
        req.response.status_code = httpstatus.HTTP_NOT_FOUND
        req.response.set_data(t(lang(req), "edit_common_noobjectsfound"))
        return
    if not node.has_read_access():
        req.response.set_data(t(lang(req), "permisssion_denied"))
        return httpstatus.HTTP_FORBIDDEN

    return node.popup_thumbbig(req)


#
# help window for metadata field
#
def show_help(req):
    if req.values.get("maskid", "") != "":
        field = q(Node).get(req.values["maskid"])
    else:
        field = q(Node).get(req.values["id"])
    if field.has_read_access():
        html = webconfig.theme.render_macro("popups.j2.jade", "show_help", {"field": field})
        req.response.status_code = httpstatus.HTTP_OK
    else:
        html = t(lang(req), "permission_denied")
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
    req.response.set_data(html)
#
# show attachmentbrowser for given node
# parameter: req.id, req.mediatum_contextfree_path
#


def show_attachmentbrowser(req):
    node = q(Node).get(req.values["id"])
    if not node.has_data_access():
        req.response.set_data(t(lang(req), "permission_denied"))
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return

    from core.attachment import getAttachmentBrowser
    getAttachmentBrowser(node, req)


RE_PRINT_URL = re.compile("/print/(\d+).pdf")


def redirect_old_printview(req):
    req.response.location = req.mediatum_contextfree_path + ".pdf"
    req.response.status_code = httpstatus.HTTP_TEMPORARY_REDIRECT
    return


def show_printview(req):
    """ create a pdf preview of given node (id in path e.g. /print/[id].pdf)"""
    match = RE_PRINT_URL.match(req.mediatum_contextfree_path)
    nodeid = int(match.group(1))

    node = q(Node).get(nodeid)
    if node.system_attrs.get("print") == "0":
        req.response.status_code = httpstatus.HTTP_NOT_FOUND
        req.response.set_data(t(lang(req), "edit_common_noobjectsfound"))
        return
    if not node.has_read_access():
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        req.response.set_data(t(lang(req), "permission_denied"))
        return

    style = int(req.values.get("style", 2))

    # nodetype
    mtype = node.metadatatype

    mask = None
    metadata = None
    if mtype:
        for m in mtype.getMasks():
            if m.getMasktype() == "fullview":
                mask = m
            if m.getMasktype() == "printview":
                mask = m
                break

        if not mask:
            mask = mtype.getMask("nodebig")

        if mask:
            metadata = mask.getViewHTML([node], VIEW_DATA_ONLY + VIEW_HIDE_EMPTY)

    if not metadata:
        metadata = [['nodename', node.getName(), 'Name', 'text']]

    # XXX: use scalar() after duplicate cleanup
    presentation_file = node.files.filter_by(filetype=u"presentation").first()
    imagepath = presentation_file.abspath if presentation_file is not None else None

    # children
    children = []
    if isinstance(node, Container):
        group_ids, ip, date = _database_postgres.build_accessfunc_arguments()
        node_ids_cte = q(_database_postgres_node.t_nodemapping.c.cid.label('nodeid'),
                         _sqlalchemy.sql.expression.literal('').label('sortpath'))\
            .filter(_database_postgres_node.t_nodemapping.c.cid == node.id).cte(recursive=True)
        node_ids_recursive = node_ids_cte.alias()
        node_ids_cte = node_ids_cte.union(
            q(_database_postgres_node.t_nodemapping.c.cid,
              _sqlalchemy.func.concat(node_ids_recursive.c.sortpath, '/', _database_postgres_node.t_nodemapping.c.cid))
                .filter(_sqlalchemy.and_(_database_postgres_node.t_nodemapping.c.nid == node_ids_recursive.c.nodeid,
                                         _sqlalchemy.func
                                         .has_read_access_to_node(_database_postgres_node.t_nodemapping.c.cid,
                                                                  group_ids, ip, date))))

        nodes = q(Node, node_ids_cte.c.sortpath).join(node_ids_cte, Node.id == node_ids_cte.c.nodeid)\
                    .order_by(node_ids_cte.c.sortpath).prefetch_attrs().all()[1:]

        base_path = tuple((getPaths(node) or ((),))[0][1:]) + (node,)
        base_path = _functools.partial(_itertools.chain, tuple(n.name for n in base_path))


        nid2node = {n.id:n for n,_ in nodes}
        schema2node = {n.schema:n for n,_ in nodes}

        @_backports_functools_lru_cache.lru_cache(maxsize=2*len(nodes))
        def get_mask(schema):
            mtype = schema2node[schema].metadatatype
            return mtype.getMask("printlist") or mtype.getMask("nodesmall")

        @_backports_functools_lru_cache.lru_cache(maxsize=2*len(nodes))
        def get_view(nid):
            node = nid2node[nid]
            return get_mask(node.schema).getViewHTML([node], VIEW_DATA_ONLY)

        for c,path in nodes:
            if not isinstance(c, Container):
                # items
                c_view = get_view(c.id)
                if len(c_view) > 0:
                    children.append(c_view)
            else:
                # header
                path_nids = tuple(_itertools.imap(int, path.split("/")[1:]))
                pathname = " > ".join(base_path(nid2node[nid].name for nid in path_nids))
                children.append([(c.id, pathname, c.name, "header")])

        if len(children) > 1:
            col = []
            order = []
            try:
                sort = getCollection(node).get("sortfield")
            except:
                logg.exception("exception in show_printview, getting sortfield failed, setting sort = \"\"")
                sort = ""

            for i in range(0, 2):
                col.append((0, ""))
                order.append(1)
                if req.values.get("sortfield" + str(i)) != "":
                    sort = req.values.get("sortfield" + unicode(i), sort)

                if sort != "":
                    if sort.startswith("-"):
                        sort = sort[1:]
                        order[i] = -1
                    _i = 0
                    for c in children[0]:
                        if c[0] == sort:
                            col[i] = (_i, sort)
                        _i += 1
                if col[i][1] == "":
                    col[i] = (0, children[0][0][0])

            # sort method for items
            def myCmp(x, y, col, order):
                cx = ""
                cy = ""
                for item in x:
                    if item[0] == col[0][1]:
                        cx = item[1]
                        break
                for item in y:
                    if item[0] == col[0][1]:
                        cy = item[1]
                        break
                if cx.lower() > cy.lower():
                    req.response.status_code = 1 * order[0]
                    return 1 * order[0]
                req.response.status_code = -1 * order[0]
                return -1 * order[0]

            sorted_children = []
            tmp = []
            for item in children:
                if item[0][3] == "header":
                    if len(tmp) > 0:
                        tmp.sort(lambda x, y: myCmp(x, y, col, order))
                        sorted_children.extend(tmp)
                    tmp = []
                    sorted_children.append(item)
                else:
                    tmp.append(item)
            tmp.sort(lambda x, y: myCmp(x, y, col, order))
            sorted_children.extend(tmp)
            children = sorted_children

    temp_download_file = _utils_utils.new_temp_download_file(u"{}.printview.pdf".format(node.get_name()))
    _web_frontend_printview.getPrintView(
        lang(req),
        imagepath,
        metadata,
        getPaths(node),
        style,
        children,
        getCollection(node),
        temp_download_file,
    )
    _sendFile(req, temp_download_file, "application/pdf")


# use popup method of  metadatatype
def popup_metatype(req):
    mtype = getMetadataType(req.mediatum_contextfree_path.split("/")[-1])
    if mtype and hasattr(mtype, "getPopup"):
        mtype.getPopup(req)
    else:
        logg.error("error, no popup method found")
