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

import core.tree as tree
from utils.utils import esc
from utils.pathutils import isDescendantOf
from .oaisetgroup import OAISetGroup as OAISetGroup

DEBUG = False
DICT_GROUPS = {}
GROUPS = []
GROUP_GETTERS = {}  # may be used to reload groups from plugins


def registerGroup(g):
    global DICT_GROUPS, GROUPS
    DICT_GROUPS[g.group_identifier] = g
    GROUPS = sorted(DICT_GROUPS.values(), key=lambda x: x.sortorder)


def registerGroupGetterFunc(key, gg_func):
    global GROUP_GETTERS
    GROUP_GETTERS[key] = gg_func
    GROUPS = sorted(DICT_GROUPS.values(), key=lambda x: x.sortorder)


def loadGroups():
    global DICT_GROUPS, GROUPS, GROUP_GETTERS
    for get_groups in GROUP_GETTERS.values():
        for g in get_groups():
            registerGroup(g)
    GROUPS = sorted(DICT_GROUPS.values(), key=lambda x: x.sortorder)


def func_getNodesForSetSpec(self, setspec, schemata):
    collection = tree.getNode(setspec)
    return [n for n in collection.getAllChildren() if n.getSchema() in schemata]


def func_getSetSpecsForNode(self, node, schemata):
    res = []
    for setspec in self.d_names.keys():
        if isDescendantOf(node, tree.getNode(setspec)):
            res.append(setspec)
    return res


def build_container_group():
    # sets configured with container attributes
    node_list = tree.NodeList(tree.getNodesByAttribute('oai.setname', '*'))
    node_list = node_list.sort_by_fields(field="oai.setname")
    node_list = [node for node in node_list if node.type in ['collection', 'directory']]
    node_list = [node for node in node_list if node.get('oai.setname').strip()]
    node_list = [node for node in node_list if node.get('oai.formats').strip()]

    d_names = OrderedDict()
    for col_node in node_list:
        d_names[str(col_node.id)] = esc(col_node.get('oai.setname'))

    g = OAISetGroup(d_names, descr='group of %d container sets' % len(d_names))

    g.func_getNodesForSetSpec = func_getNodesForSetSpec
    g.func_getSetSpecsForNode = func_getSetSpecsForNode
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


def init():
    registerGroupGetterFunc('mediatum', get_set_groups)
    loadGroups()
