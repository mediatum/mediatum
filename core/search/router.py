#!/usr/bin/python
"""
 mediatum - a multimedia content repository

 Copyright (C) 2008 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2008 Matthias Kramm <kramm@in.tum.de>

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

import sys
sys.path += ["../", "."]

import core.tree as tree
from core.search.ftsquery import FtsSearcher


class SearchRouter():
    """
    Routes queries to the proper search databases
    """

    def __init__(self):
        self.schemas = {schema[0].split('/')[1]: None
                        for schema in
                        tree.db.runQuery('''select distinct type
                                            from node
                                            where type
                                            like "%%/%%"''')}

        def init_searchers():
            for key in self.schemas:
                self.schemas[key] = FtsSearcher(key)
                self.schemas[key].initIndexer()

        init_searchers()

    def route_query(self, q):
        result = []
        for searcher in self.schemas.values():
            query_result = searcher.query(q)
            if query_result:
                result += query_result
        return list(set(result))

router = SearchRouter()
