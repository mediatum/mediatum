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
from __future__ import division
import sys
import difflib
import time
from collections import namedtuple
sys.path += ['../..', '../', '.']

from core.init import basic_init
basic_init()

import core.tree as tree
from core.search.ftsquery import protect
from utils.utils import u, modify_tex, normalize_utf8
import utils.utils
import utils.mail as mail
import logging

#Configurable, ;-separated
MAIL_RECIPIENTS = 'andrew.darrohn@tum.de;ga39lit@mytum.de'

SearchField = namedtuple('SearchField', 'position name')
searcher = tree.searcher
results = {}
schema_summary = {}
schema_db_contents = {}
schema_field_mapping = {}
zero_index_schema_field_mapping = {}
OMITTED_DB_FIELDS = ('search-',)
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
    Returns the necessary SQl to search the respective databases
    @param _type: String, type of search query
    @return: String
    """
    if _type == 'full_indexed':
        return 'select id from fullsearchmeta'
    if _type == 'ext_content':
        return 'select %s from searchmeta'
    if _type == 'ext_field_names':
        return 'select position, attrname from searchmeta_def'
    if _type == 'text_indexed':
        return 'select id from textsearchmeta'


def get_schema_fields(schema):
    """
    Fetches the schema fields from the search database and returns a list of SearchField NamedTuples
    with attributes 'name' and 'position'.
    @param schema: String, name of the schema
    @return: List
    """
    if schema not in schema_field_mapping:
        # read as: keep all fields which do not contain 'search'- or 'fulltext' in their name and then sort
        # them by their position number.
        #
        # we remove these fields due to the large overhead of querying and returning these large text values
        # for each node (sql takes too long to execute)
        field_names = [SearchField(*tup) for tup in sorted(searcher.execute(get_search_sql('ext_field_names'),
                                                                            schema,
                                                                            'ext'),
                                                           key=lambda x: int(x[0]))
                       if all(unwanted_field not in tup[1]
                              for unwanted_field in OMITTED_DB_FIELDS)]

        schema_field_mapping[schema] = field_names

    return schema_field_mapping[schema]


def get_zero_index_schema_fields(schema):
    """
    Returns a zero indexed List of SearchField NamedTuples.
    @param schema: String, name of the schema
    @return: List
    """
    if schema not in zero_index_schema_field_mapping:
        zero_index_schema_field_mapping[schema] = [SearchField(position,
                                                               tup.name) for position, tup in
                                                   enumerate(get_schema_fields(schema))]

    return zero_index_schema_field_mapping[schema]


def get_extended_field_ratio(schema, node, db_content):
    """
    Compares the values in the ext search db and the values in the node instance and returns
    a ratio of likeness between the two values.
    @param schema: String, name of the schema
    @param node: Node, an core.tree node instance
    @return: Float
    """
    ratios = []

    field_names = get_zero_index_schema_fields(schema)

    for field in field_names:
        node_value = normalize_utf8(modify_tex(u(protect(node.get(field.name))), 'strip'))
        db_value = str(db_content[field.position])
        equality_ratio = difflib.SequenceMatcher(None, db_value, node_value).ratio()
        ratios.append(equality_ratio)

    return sum(ratios) / len(ratios)


def all_schemas_summary():
    """
    Formats the data in the schema_summary dict into a table, the content of which
    are ratios regarding the completeness and correctness of the search databases
    where each row corresponds to a particular schema.
    Example Output

    ****************************************************************************************************
                                               SCHEMA SUMMARY
    ****************************************************************************************************
    Schema                                        FULL           EXT            EXT_RATIO           TEXT
    ----------------------------------------------------------------------------------------------------
    schema_name                               100.00%        100.00%             100.00%         100.00%

    Explained:
    Schema: the name of the schema
    Full: percentage of documents of the schema type which are in the full_search database
    EXT: percentage of documents of the schema type which are in the ext_search database
    EXT_RATIO: ratio of similarity between fields in the search database and the values fetched via tree.node.get()
    TEXT: percentage of documents of the schema type which are in the text_search database

    @return: String
    """
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
                                                                       schema_summary[schema]['full'],
                                                                       schema_summary[schema]['ext']['ratio'],
                                                                       schema_summary[schema]['ext']['field_ratio'],
                                                                       schema_summary[schema]['text'],
                                                                       '\n')

    return output


def main():
    """
    This script attempts to give an overview of the completeness and correctness of the
    search databases. The report will be generated by the script and sent to the emails
    which are set in the EMAIL_RECIPIENTS variable.
    """
    t = time.time()
    published_nodes = set([int(node.id) for node in tree.getNode(604993).getAllChildren() if not node.isContainer()])

    for schema in searcher.schemas:
        published_schema = published_nodes.intersection(set([int(nid[0]) for nid in
                                                             tree.db.runQuery(
                                                                 """select distinct(id) from node where type like "%{}%" """.format(
                                                                     schema))]))
        if len(published_schema) == 0:
            search_full_ratio = 0
            search_text_ratio = 0
            search_ext_ratio = 0
            search_ext_field_ratio = 0

        else:
            search_full_ratio = len(published_schema.intersection(
                set([int(nid[0]) for nid in searcher.execute(get_search_sql('full_indexed'),
                                                             schema,
                                                             'full')]))) / len(published_schema)

            search_text_ratio = len(published_schema.intersection(
                set([int(nid[0]) for nid in searcher.execute(get_search_sql('text_indexed'),
                                                             schema,
                                                             'text')]))) / len(published_schema)

            ext_content = searcher.execute(get_search_sql('ext_content') %
                                           (', '.join(['id'] + ['field' + db_field.position for
                                                                db_field in
                                                                get_schema_fields(schema)])),
                                           schema,
                                           'ext')

            if not ext_content:
                ext_processed = {}
            else:
                ext_processed = {node[0]: node[1:] for node in ext_content if int(node[0]) in published_schema}

            search_ext_ratio = len(ext_processed) / len(published_schema)

            ext_field_ratios = []
            for nid in ext_processed:
                ext_field_ratios.append(get_extended_field_ratio(schema, tree.getNode(nid), ext_processed[nid]))

            if len(ext_field_ratios) == 0:
                search_ext_field_ratio = 0
            else:
                search_ext_field_ratio = sum(ext_field_ratios) / len(ext_field_ratios)

        schema_summary[schema] = {'ext': {'ratio': search_ext_ratio,
                                          'field_ratio': search_ext_field_ratio},
                                  'full': search_full_ratio,
                                  'text': search_text_ratio}

    result = all_schemas_summary()
    print '%s sec to complete' % (time.time() - t)
    print result

    try:
        mailtext = result
        mail.sendmail('mediatum@tum.de',
                      MAIL_RECIPIENTS,
                      'Schema Analysis is Finished',
                      mailtext)

    except mail.SocketError:
        logging.getLogger('backend').error('failed to send Schema Analysis Results')


if __name__ == '__main__':
    main()
