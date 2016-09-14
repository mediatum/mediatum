"""
 mediatum - a multimedia content repository

 Copyright (C) 2008 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2008 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner Neudenberger <neudenberger@ub.tum.de>

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
from collections import OrderedDict

from utils.utils import esc
from utils.pathutils import isDescendantOf
from .oaisetgroup import OAISetGroup as OAISetGroup
from core import db, config, Node

q = db.query

DEBUG = False
DICT_GROUPS = {}
GROUPS = []
GROUP_GETTERS = {}  # may be used to reload groups from plugins


def registerGroup(g):
    global GROUPS
    DICT_GROUPS[g.group_identifier] = g
    GROUPS = sorted(DICT_GROUPS.values(), key=lambda x: x.sortorder)


def registerGroupGetterFunc(key, gg_func):
    global GROUPS
    GROUP_GETTERS[key] = gg_func
    GROUPS = sorted(DICT_GROUPS.values(), key=lambda x: x.sortorder)


def loadGroups():
    global GROUPS
    for get_groups in GROUP_GETTERS.values():
        for g in get_groups():
            registerGroup(g)
    GROUPS = sorted(DICT_GROUPS.values(), key=lambda x: x.sortorder)


def func_getNodesForSetSpec(self, setspec, schemata):
    collection = q(Node).get(setspec)
    return [n for n in collection.all_children if n.schema in schemata]


def func_getSetSpecsForNode(self, node, schemata):
    res = []
    for setspec in self.d_names.keys():
        if isDescendantOf(node, q(Node).get(setspec)):
            res.append(setspec)
    return res


def get_nodes_query_for_container_setspec(self, setspec, schemata):

    container_node = q(Node).get(setspec)
    nodequery = container_node.all_children
    nodequery = nodequery.filter(Node.schema.in_(schemata))

    return nodequery


def build_container_group():
    node_list = q(Node).filter(Node.attrs['oai.setname'].isnot(None))
    node_list = node_list.order_by(Node.attrs['oai.setname'])
    node_list = [node for node in node_list if node.type in ['collection', 'directory']]
    node_list = [node for node in node_list if node.get('oai.setname').strip()]
    node_list = [node for node in node_list if node.get('oai.formats').strip()]

    d_names = OrderedDict()
    d_filters = OrderedDict()

    for col_node in node_list:
        d_names[ustr(col_node.id)] = esc(col_node.get('oai.setname'))
        d_filters[ustr(col_node.id)] = None  # todo: fix this

    g = OAISetGroup(d_names, descr='group of %d container sets' % len(d_names))

    g.func_getNodesForSetSpec = func_getNodesForSetSpec
    g.func_getSetSpecsForNode = func_getSetSpecsForNode
    g.func_get_nodes_query_for_setspec = get_nodes_query_for_container_setspec
    g.sortorder = '040'
    g.group_identifier = 'oaigroup_containers'
    return g


def get_set_groups():
    res = []
    res += [build_container_group()]
    return res


def getNodes(setspec, schemata):
    for g in GROUPS:
        if setspec in g.d_names.keys():
            return g.getNodesForSetSpec(setspec, schemata)
    return []


def getNodesFilterForSetSpec(setspec, schemata):
    for g in GROUPS:
        if setspec in g.d_names.keys():
            return g.getNodesFilterForSetSpec(setspec, schemata)
    return []


def getNodesQueryForSetSpec(setspec, schemata):
    for g in GROUPS:
        if setspec in g.d_names.keys():
            if g.func_get_nodes_query_for_setspec:
                return g.func_get_nodes_query_for_setspec(g, setspec, schemata)
    return None


def getSets():
    res = []
    for g in GROUPS:
        res += g.d_names.items()
    return res


def getSetSpecsForNode(node):
    res = []
    for g in GROUPS:
        res += g.getSetSpecsForNode(node, '')
    return res


def getGroup(group_identifier):
    return DICT_GROUPS[group_identifier]


def existsSetSpec(setspec):
    '''
    :param setspec: string
    :return: True if setspec is defined, False otherwise

    this function has been introduced to allow to respond early with an oai error
    '''
    for g in GROUPS:
        if setspec in g.d_names.keys():
            return True
    return False


def init():
    if config.getboolean("oai.activate", True):
        registerGroupGetterFunc('mediatum', get_set_groups)
        loadGroups()
