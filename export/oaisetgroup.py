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

import logging


logg = logging.getLogger(__name__)


class OAISetGroup:

    def __init__(self, d_names, d_queries={}, d_filters={},
                 func_getNodesForSetSpec=None,
                 func_getSetSpecsForNode=None,
                 func_isSetEmpty=None,
                 func_get_nodes_query_for_setspec= None,
                 descr='-undescribed OAI set group-',
                 sortorder='',
                 group_identifier=''):
        self.d_names = d_names
        self.d_queries = d_queries
        self.d_filters = d_filters
        self.func_getNodesForSetSpec = func_getNodesForSetSpec
        self.func_getSetSpecsForNode = func_getSetSpecsForNode
        self.func_isSetEmpty = func_isSetEmpty
        self.func_get_nodes_query_for_setspec = func_get_nodes_query_for_setspec
        self.descr = descr
        self.sortorder = sortorder
        self.group_identifier = group_identifier

    def __str__(self):
        return self.descr

    def __repr__(self):
        return "<%s>" % self.descr

    def getSetSpecs(self):
        return self.d_names.keys()

    def getSpecNameItems(self):
        return self.d_names.items()

    def getNodesForSetSpec(self, setspec, schemata):
        if self.func_getNodesForSetSpec:
            return self.func_getNodesForSetSpec(self, setspec, schemata)
        elif setspec in self.d_filters:
            setspecFilter = self.d_filters.get(setspec)
            return setspecFilter
            from .oaisearchparser import OAISearchParser
            osp = OAISearchParser()
            res = osp.parse(self.d_queries[setspec]).execute()
            if setspec in self.d_filters:
                nodefilter = self.d_filters[setspec]
                res = [n.id for n in res if nodefilter(setspec, n)]
            return res
        else:
            logg.error("OAI: Error: no function 'getNodesForSetSpec' found for setSpec='%s', returning empty list", setspec)
            return []

    def getNodesFilterForSetSpec(self, setspec, schemata):
        if setspec in self.d_filters:
            setspecFilter = self.d_filters.get(setspec)
            return setspecFilter
        else:
            logg.error("OAI: Error: no function 'getNodesForSetSpec' found for setSpec='%s', returning empty list", setspec)
            return []

    def getSetSpecsForNode(self, node, schemata=[]):
        if self.func_getSetSpecsForNode:
            return self.func_getSetSpecsForNode(self, node, schemata=[])
        elif self.d_queries:
            from .oainodechecker import OAINodeChecker
            onc = OAINodeChecker()
            erg = []
            for setspec, query in self.d_queries.items():
                if onc.parse(query).execute(node):
                    if setspec in self.d_filters:
                        nodefilter = self.d_filters[setspec]
                        if nodefilter(setspec, node):
                            erg.append(setspec)
                    else:
                        erg.append(setspec)
            return erg
        else:
            logg.error("OAI: Error: set group %s: no function 'getSetSpecsForNode' found for node.id='%s', node.type='%s', returning empty list",
                self, node.id, node.type)
            return []

    def isSetEmpty(self, node, schemata=[]):
        if self.func_isSetEmpty:
            return self.func_isSetEmpty(self, node, schemata=[])
        return False
