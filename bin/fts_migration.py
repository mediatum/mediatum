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
import sqlite3

from core.init import basic_init
basic_init()

import core.tree as tree
import core.config as config


def main():
    """
    This script splits up the current fts3 database scheme by schema. This is required in order to maintain your
    search database indexes after altering the way our fts3 searcher works.

    With the new fts searcher, your searchstore folder will now be populated as follows:

    If you are currently using a non split database, you will then have a
        {schema_name}_searchindex.db
    for each schema in the database.

    If you are currently using a split database, you will have a
        {schema_name}_searchindex_full.db
        {schema_name}_searchindex_text.db
        {schema_name}_searchindex_ext.db
    for each schema in the database.

    This script will not remove your current database(s), but rather copy the indexes over to their new database.
    """
    searcher_type = config.get('config.searcher')
    db_scheme = config.get('database.searchdb', 'std')
    search_folder = config.get('paths.searchstore')

    db_extensions = {'std': {'full': '',
                             'text': '',
                             'ext': ''},
                     'split': {'full': '_full',
                               'text': '_text',
                               'ext': '_ext'}}

    current_dbs = {key: 'searchindex%s.db' % value
                   for key, value
                   in db_extensions[db_scheme].items()}

    schemas = list(set([schema[0].split('/')[1]
                        for schema in
                        tree.db.runQuery('''select distinct type
                                            from node
                                            where type
                                            like "%%/%%"''')]))

    tablenames = {'full': [('fullsearchmeta', 'schema')],
                  'ext': [('searchmeta', 'schema'),
                          ('searchmeta_def', 'name')],
                  'text': [('textsearchmeta', 'schema')]}

    if searcher_type == 'fts3':
        for db_type, db_name in current_dbs.items():
            connection = sqlite3.connect('%s%s' % (search_folder,
                                                   db_name))
            cursor = connection.cursor()
            for schema in schemas:
                cursor.execute("""ATTACH DATABASE "%s%s_%s%s%s" as OTHER""" % (search_folder,
                                                                               schema,
                                                                               'searchindex',
                                                                               db_extensions[db_scheme][db_type],
                                                                               '.db'))

                for table in tablenames[db_type]:
                    cursor.execute("""INSERT INTO OTHER.%s SELECT * FROM %s WHERE %s="%s" """ % (table[0],
                                                                                                 table[0],
                                                                                                 table[1],
                                                                                                 schema))

                cursor.execute('DETACH OTHER')

    else:
        print 'Not using an fts3 db'


if __name__ == '__main__':
    main()