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
import utils.mail as mail
import logging


SearchField = namedtuple('SearchField', 'position name')
searcher = tree.searcher
results = {}
schema_db_contents = {}
schema_field_mapping = {}
zero_index_schema_field_mapping = {}
omitted_db_fields = ('search-',)
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


def is_indexed(schema, db_type, id):
    """
    Checks to see if the node is indexed in the corresponding database

    @param schema: str the name of the schema
    @param db_type: str one of the following: 'full', 'ext', 'text'
    @param id: str the node id
    @return: bool True or False
    """
    if db_type == 'text':
        return id in schema_db_contents[schema][db_type]
    else:
        return id in schema_db_contents[schema][db_type].keys()


def calculate_percentage(summary_list):
    """
    Calculates an average from a given list whose contents are either 0,1 or True/False
    @param summary_list: list of summary values
    @return: float percentage as decimal
    """
    if len(summary_list) == 0:
        return 0
    else:
        return float(sum(summary_list)) / len(summary_list)


def get_content_full(schema, db_type, id):
    """
    Retrieves content from the
    @param schema:
    @param db_type:
    @param id:
    @return:
    """
    if not is_indexed(schema, db_type, id):
        return {}
    else:
        return schema_db_contents[schema][db_type][id]


def get_content_ext(schema, db_type, node):
    """

    @param schema:
    @param db_type:
    @param node:
    @return:
    """
    if not is_indexed(schema, db_type, node.id):
        return {}
    else:
        return compare_extended_fields(schema, node)


def get_search_sql(_type):
    """

    @param _type:
    @return:
    """
    if _type == 'full_content':
        return 'select id, value from fullsearchmeta'
    if _type == 'ext_content':
        return 'select %s from searchmeta'
    if _type == 'ext_field_names':
        return 'select position, attrname from searchmeta_def'
    if _type == 'text_indexed':
        return 'select id from textsearchmeta'


def get_schema_fields(schema):
    """

    @param schema:
    @return:
    """
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

    return schema_field_mapping[schema]

def get_zero_index_schema_fields(schema):
    """

    @param schema:
    @return:
    """
    if schema not in zero_index_schema_field_mapping:
        zero_index_schema_field_mapping[schema] = [SearchField(position,
                                                               tup.name) for position, tup in enumerate(get_schema_fields(schema))]

    return zero_index_schema_field_mapping[schema]

def compare_extended_fields(schema, node):
    """
    @param schema:
    @param node:
    @return:
    """
    content = {}


    field_names = get_zero_index_schema_fields(schema)

    db_content = schema_db_contents[schema]['ext'][node.id]

    for field in field_names:
        node_value = normalize_utf8(modify_tex(u(protect(node.get(field.name))), 'strip'))
        db_value = str(db_content[field.position])
        equality_ratio = difflib.SequenceMatcher(None, db_value, node_value).ratio()

        content[field.name] = {'search_value': db_value,
                               'node_value': node_value,
                               'ratio': equality_ratio}

    return content


def node_summary(id):
    """

    @param id:
    @return:
    """
    node = results[str(id)]
    avg_ratio = sum([node['ext']['content'][field]['ratio'] for field in node['ext']['content']]) / 24
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


def all_schemas_summary():
    schema_summary = {}
    for schema in searcher.schemas:
        schema_summary[schema] = {'ext': {'percentage': [],
                                          'ratio': []},
                                  'full': [],
                                  'text': []}

    for node in results.keys():
        if results[node]['ext']['is_indexed']:
            schema_summary[tree.getNode(node).getSchema()]['ext']['ratio'].append(
                sum([results[node]['ext']['content'][field]['ratio'] for field in results[node]['ext']['content']]) / len(
                    results[node]['ext']['content'].keys()))
        schema_summary[tree.getNode(node).getSchema()]['ext']['percentage'].append(
            results[node]['ext']['is_indexed'])
        schema_summary[tree.getNode(node).getSchema()]['full'].append(
            results[node]['full']['is_indexed'])
        schema_summary[tree.getNode(node).getSchema()]['text'].append(
            results[node]['text']['is_indexed'])

    output = '{}{}{:^100}{}{}{}{:46}{:15}{:15}{:20}{:15}{}{}{}'.format('*' * 100,
                                                                       '\n',
                                                                       'SCHEMA SUMMARY',
                                                                       '\n',
                                                                       '*' * 100,
                                                                       '\n',
                                                                       'Schema',
                                                                       'FULL',
                                                                       'EXT',
                                                                       'EXT_RATIO',
                                                                       'TEXT',
                                                                       '\n',
                                                                       '-' * 100,
                                                                       '\n')
    for schema in schema_summary.keys():
        output += '{:35}{:>15.2%}{:>15.2%}{:>20.2%}{:>15.2%}{}'.format(schema,
                                                                       calculate_percentage(
                                                                           schema_summary[schema]['full']),
                                                                       calculate_percentage(
                                                                           schema_summary[schema]['ext']['percentage']),
                                                                       calculate_percentage(
                                                                           schema_summary[schema]['ext']['ratio']),
                                                                       calculate_percentage(
                                                                           schema_summary[schema]['text']),
                                                                       '\n')

    return output


def main():
    """

    @return:
    """
    t = time.time()
    published_nodes = (node for node in tree.getNode(604993).getAllChildren() if not node.isContainer())

    for schema in searcher.schemas:
        schema_db_contents[schema] = {'full': {},
                                      'ext': {},
                                      'text': {}}

        full = searcher.execute(get_search_sql('full_content'),
                                schema,
                                'full')

        if not full:
            full_processed = {}
        else:
            full_processed = {node[0]: node[1:][0] for node in full}

        ext = searcher.execute(get_search_sql('ext_content') %
                               (', '.join(['id'] + ['field' + db_field.position for
                                                    db_field in
                                                    get_schema_fields(schema)])),
                               schema,
                               'ext')
        if not ext:
            ext_processed = {}
        else:
            ext_processed = {node[0]: node[1:] for node in ext}

        schema_db_contents[schema] = {'full': full_processed,
                                      'ext': ext_processed,
                                      'text': [id[0] for id in searcher.execute(get_search_sql('text_indexed'),
                                                                                schema,
                                                                                'text')]}

    for node in published_nodes:
        schema = node.getSchema()

        if schema not in searcher.schemas:
            continue
        else:
            results[node.id] = {'schema': schema,
                                'full': {'is_indexed': is_indexed(schema,
                                                                  'full',
                                                                  node.id),
                                         'content': get_content_full(schema, 'full', node.id)},

                                'ext': {'is_indexed': is_indexed(schema,
                                                                 'ext',
                                                                 node.id),
                                        'content': get_content_ext(schema, 'ext', node)},
                                'text': {'is_indexed': is_indexed(schema,
                                                                  'text',
                                                                  node.id)}}

    result = all_schemas_summary()
    print '%s sec to complete' % (time.time() - t)
    print result

    try:
        mailtext = result
        mail.sendmail('andrew.darrohn@tum.de',
                      'andrew.darrohn@tum.de',
                      'Schema Analysis is Finished',
                      mailtext)

    except mail.SocketError:
        logging.getLogger('backend').error('failed to send Schema Analysis Results')


if __name__ == '__main__':
    main()



