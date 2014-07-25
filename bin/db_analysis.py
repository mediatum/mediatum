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
import difflib
import time
import sqlite3
import pickle
import json
from collections import namedtuple
from pprint import pprint as pp

sys.path += ['../..', '../', '.']

import core.tree as tree
from core.search.ftsquery import protect
from utils.utils import u, modify_tex, normalize_utf8
import utils.utils


SearchField = namedtuple('SearchField', 'position name')
searcher = tree.searcher
results = {}
schema_field_mapping = {}
omitted_db_fields = ('search-', 'fulltext')
utils.utils.normalization_items = {"chars": [("00e4", "ae"),
                                 ("00c4", "Ae"),
                                 ("00df", "ss"),
                                 ("00fc", "ue"),
                                 ("00dc", "Ue"),
                                 ("00f6", "oe"),
                                 ("00d6", "Oe"),
                                 ("00e8", "e"),
                                 ("00e9", "e")],
                       "words": []}


def get_search_sql(_type):
    """

    @param _type:
    @return:
    """
    if _type == 'full_indexed':
        return 'select distinct(id) from fullsearchmeta where id="%s"'
    if _type == 'full_content':
        return 'select value from fullsearchmeta where id="%s"'
    if _type == 'ext_indexed':
        return 'select distinct(id) from searchmeta where id="%s"'
    if _type == 'ext_content':
        return 'select %s from searchmeta where id="%s"'
    if _type == 'ext_field_names':
        return 'select position, attrname from searchmeta_def'
    if _type == 'text_indexed':
        return 'select id from textsearchmeta where id="%s"'


def compare_extended_fields(schema, node):
    """

    @param schema:
    @param node:
    @return:
    """
    content = {}
    t = time.time()
    if schema not in schema_field_mapping:
        #read as: keep all fields which do not contain 'search'- or 'fulltext' in their name and then sort
        #them by their position number.
        #
        #we remove these fields due to the large overhead of querying and returning these large text values
        #for each node (sql takes too long to execute)
        field_names = [SearchField(*tup) for tup in sorted(searcher.execute(get_search_sql('ext_field_names'),
                                                                            schema,
                                                                            'ext'),
                                                           key=lambda x: int(x[0]))
                       if all(unwanted_field not in tup[1]
                              for unwanted_field in omitted_db_fields)]

        schema_field_mapping[schema] = field_names
    else:
        field_names = schema_field_mapping[schema]

    print '%s sec to get field_names' % str(time.time() - t)
    t = time.time()

    #[4:] removes unnecessary data so that only searchfields are present
    db_content = searcher.execute(get_search_sql('ext_content') % (', '.join(['field' + db_field.position for
                                                                              db_field in field_names]),
                                                                   node.id),
                                  schema,
                                  'ext')[0]

    print '%s sec to get db_content' % str(time.time() - t)
    t = time.time()
    for field in field_names:
        node_value = normalize_utf8(modify_tex(u(protect(node.get(field.name))), 'strip'))
        db_value = db_content[int(field.position) - 6]
        equality_ratio = difflib.SequenceMatcher(None, db_value, node_value).ratio()

        content[field.name] = {'search_value': db_value,
                               'node_value': node_value,
                               'ratio': equality_ratio}
    print '%s sec to populate content' % str(time.time() - t)

    return content


def node_summary(id):
    """

    @param id:
    @return:
    """
    node = results[str(id)]
    avg_ratio = sum([node['ext']['content'][field]['ratio'] for field in node['ext']['content']]) / 29
    print '{}{}{:^30}{}{}{}{:>18}{:>12}{}{:>18}{:>12}{}{:>18}{:>12}{}{:>18}{:>12}{}{:>18}{:>12}{}{:>18}{:>12.2%}'.format(
        '*' * 30,
        '\n',
        'SUMMARY',
        '\n',
        '*' * 30,
        '\n',
        'Node',
        str(id),
        '\n',
        'Schema',
        node['schema'],
        '\n',
        'full',
        node['full']['is_indexed'],
        '\n',
        'ext',
        node['ext']['is_indexed'],
        '\n',
        'text',
        node['text']['is_indexed'],
        '\n',
        'Ratio',
        avg_ratio)


def schema_summary(schema):
    """

    @param schema:
    @return:
    """
    schema_nodes = set([node_id[0] for node_id in
                        tree.db.runQuery('select cast(id as char) from node where type like "%{}%"'.format(schema))])
    published_nodes = set([node_id.id for node_id in tree.getNode(604993).getAllChildren()])

    nodes_to_analyze = list(schema_nodes.intersection(published_nodes))


def directory_summary(node):
    """

    @param node:
    @return:
    """
    pass


def overall_summary(node):
    """

    @param node:
    @return:
    """
    pass


def main():
    '''

    '''
    indexed = lambda x: True if x else False
    t1 = time.time()
    print 'fetching all published nodes...'
    published_nodes = (node for node in tree.getNode(603845).getAllChildren() if not node.isContainer())
    print '%f sec' % (time.time() - t1)

    print 'analyzing nodes...'

    t1 = time.time()
    for node in published_nodes:
        schema = node.getSchema()

        results[node.id] = {'schema': schema,
                            'full': {'is_indexed': indexed(searcher.execute(get_search_sql('full_indexed') % node.id,
                                                                            schema,
                                                                            'full')),
                                     'content': searcher.execute(get_search_sql('full_content') % node.id,
                                                                 schema,
                                                                 'full')},
                            'ext': {'is_indexed': indexed(searcher.execute(get_search_sql('ext_indexed') % node.id,
                                                                           schema,
                                                                           'ext')),
                                    'content': compare_extended_fields(schema,
                                                                       node)},
                            'text': {'is_indexed': indexed(searcher.execute(get_search_sql('text_indexed') % node.id,
                                                                            schema,
                                                                            'text'))}}
    print '%f sec' % (time.time() - t1)


if __name__ == '__main__':
    main()