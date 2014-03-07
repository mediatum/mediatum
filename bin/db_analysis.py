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
import time

SEARCHSTORE = config.get('paths.searchstore')
DATADIR = config.get('paths.tempdir')
EXT_DB = SEARCHSTORE + 'searchindex_ext.db'
FULL_SEARCH_DB = SEARCHSTORE + 'searchindex_full.db'
TEXT_SEARCH_DB = SEARCHSTORE + 'searchindex_text.db'
DBAndTable = namedtuple('DBAndTable', ['db', 'table'])

def main():
    '''
    This script runs several metrics regarding the sqlite and mysql database in order to get a scope of the current status
    The following metrics are run:
        1. Searches the sqlite database for nodes that are in the working tree but are not yet indexed in either/any of the 3 tables
        2. Searches the sqlite database for nodes that have since been removed from the working tree but are still indexed somewhere in the sqlite database
        3. Searches the mysql database for nodes which have empty attribute values
        4. Searches the mysql database for nodes which exist in the nodeattribute table but no longer exist in node
        4. Searches the mysql database for nodes which exist in the nodefile table but no longer exist in node

    The results are dumped into a .json in the configured tmp folder where the following dictionary keys correspond to the metrics above:
        sqlite_not_indexed : 1
            type: {'key': ['str, ...']}
        sqlite_deleted_nodes: 2
            type: ['str', ...]
        mysql_empty_attribute: 3
            type: ['str', ...]
        mysql_nodeattribute_not_in_node: 4
            type: ['str', ...]
        mysql_nodefile_not_in_node: 5
            type: ['str', ...]

        where 'str' corresponds to a node id
    '''

    start = time.time()
    # see what nodes are not in the search db
    #dict that will be dumped to json; keys represent the number of search dbs the node is present in
    in_num_dbs = {'0': [], '1': [], '2': [], '3': []}

    #make db connections
    db_ext = DBAndTable(sqlite.SQLiteConnector(EXT_DB), 'searchmeta')
    db_full = DBAndTable(sqlite.SQLiteConnector(FULL_SEARCH_DB), 'fullsearchmeta')
    db_text = DBAndTable(sqlite.SQLiteConnector(TEXT_SEARCH_DB), 'textsearchmeta')

    #gets all nodes for each db table
    ext_list = [node for node in zip(*db_ext.db.execute('select id from %s' % db_ext.table))[0]]
    full_list = [node for node in zip(*db_full.db.execute('select id from %s' % db_full.table))[0]]
    text_list = [node for node in zip(*db_text.db.execute('select id from %s' % db_text.table))[0]]

    #get all nodes that have parent and are not a container type
    nodes_to_scan = (node for node in zip(*tree.db.runQuery('select cast(id as char) from node where type like "%/%" and id in (select cid from nodemapping)'))[0])

    for node in nodes_to_scan:
        node_in_db = {'ext': False, 'full': False, 'text': False}
        if node in ext_list:
            node_in_db['ext'] = True
        if node in full_list:
            node_in_db['full'] = True
        if node in text_list:
            node_in_db['text'] = True
        #determines under which dict key the node should land
        priority = sum(node_in_db.values())
        #id is set last so we are able to use the sum command above
        node_in_db['id'] = node
        in_num_dbs[str(priority)].append(node_in_db)

    # see what nodes are in the search db that no longer exist in mediatum
    search_nodes_set = set(ext_list + full_list + text_list)
    mediatum_nodes = [node for node in zip(*tree.db.runQuery('select cast(id as char) from node'))[0]]
    no_longer_exist = [node for node in search_nodes_set if node not in mediatum_nodes]

    # see what nodes have empty attribute values
    empty_attribute_nodes = [node for node in zip(*tree.db.runQuery('select cast(nid as char) from nodeattribute where value = "" or value is null'))[0]]

    # see what nodes are in nodeattribute/nodefile that arent in node
    nodeattribute_not_in_node = [node for node in zip(*tree.db.runQuery('select distinct cast(nid as char) from nodeattribute where nid not in (select id from node)'))[0]]
    nodefile_not_in_node = [node for node in zip(*tree.db.runQuery('select distinct cast(nid as char) from nodefile where nid not in (select id from node)'))[0]]

    json_dump = {'sqlite_not_indexed': in_num_dbs,
                 'sqlite_deleted_nodes': no_longer_exist,
                 'mysql_empty_attribute': empty_attribute_nodes,
                 'mysql_nodeattribute_not_in_node': nodeattribute_not_in_node,
                 'mysql_nodefile_not_in_node': nodefile_not_in_node
    }

    with open(DATADIR + 'indexer_analysis.json', 'w') as f:
        json.dump(json_dump, f, indent=4)
    f.close()

    print 'Time to complete: ' + str((time.time() - start) / 60.)
    print 'Overview'
    print 'Length of Lists'
    for data in sorted(json_dump):
            if isinstance(json_dump[data], list):
                print data + ': ' + str(len(json_dump[data]))
            if isinstance(json_dump[data], dict):
                for key in sorted(json_dump[data]):
                    print data + '[' + key + ']' + ': ' + str(len(json_dump[data][key]))

if __name__ == '__main__':
    main()