#!/usr/bin/python
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

import sys
sys.path += ['../..', '../', '.']
import core.tree as tree
import core.db.sqliteconnector as sqlite
import core.config as config
import json
from collections import namedtuple

SEARCHSTORE = config.get('paths.searchstore')
DATADIR = config.get('paths.datadir')
EXT_DB = SEARCHSTORE + 'searchindex_ext.db'
FULLTEXT_SEARCH_DB = SEARCHSTORE + 'searchindex_full.db'
TEXT_SEARCH_DB = SEARCHSTORE + 'searchindex_text.db'
DBAndTable = namedtuple('DBAndTable', ['db', 'table'])

def main():
    #dict that will be dumped to json; keys represent the number of search dbs the node is present in
    in_num_dbs = {'0': [], '1': [], '2': [], '3': []}

    #make db connections
    db_ext = DBAndTable(sqlite.SQLiteConnector(EXT_DB), 'searchmeta')
    db_fulltext = DBAndTable(sqlite.SQLiteConnector(FULLTEXT_SEARCH_DB), 'fullsearchmeta')
    db_text = DBAndTable(sqlite.SQLiteConnector(TEXT_SEARCH_DB), 'textsearchmeta')

    #gets all nodes for each db table
    ext_list = [i for i in zip(*db_ext.db.execute('select id from %s' % db_ext.table))[0]]
    fulltext_list = [i for i in zip(*db_fulltext.db.execute('select id from %s' % db_fulltext.table))[0]]
    text_list = [i for i in zip(*db_text.db.execute('select id from %s' % db_text.table))[0]]

    #get all nodes that have parent and are not a container type
    nodes_to_scan = (i for i in zip(*tree.db.runQuery('select cast(id as char) from node where type like "%/%" and id in (select cid from nodemapping)'))[0])

    for node in nodes_to_scan:
        node_in_db = {'ext': False, 'fulltext': False, 'text': False}
        if node in ext_list:
            node_in_db['ext'] = True
        if node in fulltext_list:
            node_in_db['fulltext'] = True
        if node in text_list:
            node_in_db['text'] = True
        #determines under which dict key the node should land
        priority = sum(node_in_db.values())
        #id is set last so we are able to use the sum command above
        node_in_db['id'] = node
        in_num_dbs[str(priority)].append(node_in_db)

    with open(DATADIR + 'indexer_analysis.json', 'w') as f:
        json.dump(in_num_dbs, f)
    f.close()

if __name__ == '__main__':
    main()

