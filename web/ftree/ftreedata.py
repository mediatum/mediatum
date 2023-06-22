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
import core.systemtypes as _core_systemtypes
import core.translation as _core_translation
import core.users as _core_users
import core.httpstatus as _httpstatus
import utils.utils as _utils
import web.edit.edit_common as _web_edit_common
import web.edit.edit as _web_edit_edit



def getData(req):
    pid = int(req.values.get("parentId"))
    language = _core_translation.set_language(req.accept_languages)
    ret = []
    user_home_dir = _core_users.user_from_session().home_dir
    group_ids, ip, date = _database_postgres.build_accessfunc_arguments()
    nids = req.values.get("nids")
    initial_opened_nids = _get_path_to(map(int, nids.split(',')), "publish", True) if nids else req.values["path"].split(',')
    initial_opened_nids = frozenset(initial_opened_nids)
    initial_opened_nids = frozenset(int(p) for p in initial_opened_nids if p[0] not in "x(")
    del nids

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

    if pid in initial_opened_nids:
        has_writable_container_children_stmt = (_contenttypes.Container.id
                .in_(initial_opened_nids)
                .label("has_writable_container_children")
               )
    else:
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
            label = _web_edit_common.get_edit_label(c.Container, language)

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

            ret.append(u"""
                <li class="{0}.gif" id="Node{2}">
                    <a href="#" title="{1} ({2})" id="{2}" class="{3}">
                        {1}
                        <input type="image" src="/static/img/webtree/uncheck.gif"/>
                    </a>
                """.format(cls, label, c.Container.id, itemcls))

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


def _get_parents_recursive(node, _path=None):
    _path = _path or list()
    node = node.getActiveVersion()
    if isinstance(node, _core_systemtypes.Root):
        return
    for parent in node.getParents():
        _path.append(parent)
        if not isinstance(parent, _contenttypes.Collections):
            _get_parents_recursive(parent, _path)
    return _path


def _get_paths(node):
    path = []
    omit = False
    for node in _get_parents_recursive(node):
        if node.type not in ("home", "root") and not node.has_read_access():
            omit = True
            continue
        if node.type in ("directory", "home", "collection") or node.type.startswith("directory"):
            path.append(node)
        if isinstance(node, (_contenttypes.Collections, _core_systemtypes.Root)):
            if path and not omit:
                path.reverse()
                yield path
            omit = False
            path = []


def _get_path_to(path_to, style, multiselect):
    # returns path(s) to selected node, 'x' separated, with selected nodes in ()
    # parameters: pathTo=selected Node
    collectionsid = _core_nodecache.get_collections_node().id
    # if more than one node selected use the first to get the path to
    items = []
    checked = set()
    for nid in path_to:
        checked.clear()
        node = _core.db.query(_core.Node).get(nid)

        for path in _get_paths(node):
            if node.id not in path and node.isContainer():  # add node if container
                path.append(node)

            checked.add(path[-1].id)  # last item of path is checked

            if path[0].parents[0].id == collectionsid and collectionsid not in items:
                items.append(collectionsid)

            for item in path:
                if item.id not in items:
                    items.append(item.id)

            items.append("x")  # set devider for next path
            if not multiselect:  # if not multiselect use only first path
                break

    if style == "publish":
        checked.clear() # no pre-checked checkmarks in quick publisher
    elif style not in ("classification", "edittree"):
        raise RuntimeError("unknown tree style")
    items = items or (str(collectionsid), )
    return (("({})" if i in checked else "{}").format(i) for i in items)


def getPathTo(req):
    req.response.status_code = _httpstatus.HTTP_OK
    req.response.set_data(unicode(",".join(_get_path_to(
        map(int,req.values["pathTo"].split(",")),
        req.values["style"],
        req.params.get("multiselect", "false") != "false",
       ))))
