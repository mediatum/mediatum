# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import sqlalchemy as _sqlalchemy
import sqlalchemy.orm as _sqlalchemy_orm
import contenttypes as _contenttypes
import core as _core
import core.database.postgres as _database_postgres
import core.database.postgres.node as _node
import core.nodecache as _core_nodecache
import core.translation as _core_translation
import core.users as _core_users
import core.httpstatus as _httpstatus
import utils.pathutils as _pathutils
import utils.utils as _utils
import web.edit.edit_common as _web_edit_common
import web.edit.edit as _web_edit_edit



def getData(req):
    pid = req.params.get("parentId")
    assert tuple(req.values.getlist("style"))==("classification",)
    ret = []
    user_home_dir = _core_users.user_from_session().home_dir
    group_ids, ip, date = _database_postgres.build_accessfunc_arguments()

    write_access_alias = _sqlalchemy_orm.aliased(_core.Node)
    write_access_stmt = (_core.db.query(_sqlalchemy.func.has_write_access_to_node(write_access_alias.id, group_ids, ip, date))
            .filter(write_access_alias.id == _contenttypes.Container.id)
            .label('write_access')
           )

    has_container_children_alias = _sqlalchemy_orm.aliased(_contenttypes.Container)
    has_container_children_stmt = (_core.db.query(has_container_children_alias)
            .join(_node.t_nodemapping, _node.t_nodemapping.c.cid == has_container_children_alias.id)
            .filter(_node.t_nodemapping.c.nid == _contenttypes.Container.id)
            .exists()
            .label("has_container_children")
           )

    has_writable_container_alias = _sqlalchemy_orm.aliased(_contenttypes.Container)
    has_writable_container_children_stmt = (_core.db.query(has_writable_container_alias)
            .join(_node.t_noderelation, _node.t_noderelation.c.cid == has_writable_container_alias.id)
            .filter(_node.t_noderelation.c.nid == _contenttypes.Container.id)
            .filter_read_access()
            .filter_write_access()
            .exists()
            .label("has_writable_container_children")
           )

    query_container = _core.db.query(
            _contenttypes.Container,
            write_access_stmt,
            has_container_children_stmt,
            has_writable_container_children_stmt,
           )
    query_container = (query_container
        .join(_node.t_nodemapping, _node.t_nodemapping.c.cid == _contenttypes.Container.id)
        .filter(_node.t_nodemapping.c.nid == pid)
        .filter(_sqlalchemy.func.has_read_access_to_node(_contenttypes.Container.id, group_ids, ip, date))
        .prefetch_attrs()
        .prefetch_system_attrs()
        .order_by(_core.Node.orderpos)
       )

    for c in query_container:

        with _utils.suppress(Exception):
            special_dir_type = _web_edit_edit.get_special_dir_type(c.Container)
            if not c.write_access and not c.has_writable_container_children:
                continue
            label = _web_edit_common.get_edit_label(c.Container, _core_translation.set_language(req.accept_languages))
            title = u"{} ({})".format(label, c.Container.id)

            cls = "folder"

            itemcls = ""
            if not c.write_access:
                itemcls = "read"

            if c.Container.type == "collection":  # or "collection" in c.type:
                cls = "collection"
            if hasattr(c.Container, 'treeiconclass'):
                cls = c.Container.treeiconclass()

            if special_dir_type == u'trash':
                cls = "trashicon"
            elif special_dir_type == u'upload':
                cls = "uploadicon"
            elif c.Container == user_home_dir:
                cls = "homeicon"

            ret.append(u'<li class="{}.gif" id="Node{}">'.format(cls, c.Container.id))
            ret.append(u'<a href="#" title="{}" id="{}" class="{}">{}<input type="image" src="/static/img/ftree/uncheck.gif"/></a>'.format(
                            title, c.Container.id, itemcls, label))

            if c.has_container_children:
                ret.append(u'<ul><li parentId="{}" class="spinner.gif"><a href="#">&nbsp;</a></li></ul>'.format(c.Container.id))

            ret.append(u'</li>')

    req.response.set_data(u"\n".join(ret))
    req.response.status_code = _httpstatus.HTTP_OK


def getLabel(req):
    node = _core.db.query(_core.Node).get(req.params.get("getLabel"))

    inum = len(node.content_children)
    label = node.getLabel()
    if inum > 0:
        label += u" <small>({})</small>".format(inum)
    req.response.status_code = _httpstatus.HTTP_OK
    req.response.set_data(label)


def getPathTo(req):
    # returns path(s) to selected node, 'x' separated, with selected nodes in ()
    # parameters: pathTo=selected Node
    collectionsid = _core_nodecache.get_collections_node().id
    # if more than one node selected use the first to get the path to
    items = []
    for nid in req.values["pathTo"].split(','):
        node = _core.db.query(_core.Node).get(nid)

        for path in _pathutils.getPaths(node):
            if node.id not in path and node.isContainer():  # add node if container
                path.append(node)

            if path[0].parents[0].id == collectionsid and collectionsid not in items:
                items.append(collectionsid)

            for item in path:
                if item.id not in items:
                    items.append(item.id)

            items.append("x")  # set devider for next path
            if req.params.get("multiselect", "false") == "false":  # if not multiselect use only first path
                break

    items = u",".join(map(unicode, items)) or unicode(collectionsid)

    req.response.status_code = _httpstatus.HTTP_OK
    req.response.set_data(items)
