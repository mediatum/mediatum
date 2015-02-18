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
sys.path += ["../", "."]
import re
import os
import codecs
import core
import core.config as config
import core.db.sqliteconnector as sqlite
from utils.utils import normalize_utf8
from utils.date import format_date

from utils.utils import iso2utf8, esc, u

MAX_SEARCH_FIELDS = 32
DB_NAME = 'searchindex.db'
FULLTEXT_INDEX_MODE = 0

SYSTEMATTRS = ['updateuser', 'updatetime', 'edit.lastmask', 'creationtime', 'creator']


def protect(s):
    return s.replace('"', '')


class SearchIndexer:

    def __init__(self, option=""):
        try:
            self.init(option)
        except:
            print "sqlite indexer failed"

    def init(self, option):
        global MAX_SEARCH_FIELDS
        global DB_NAME
        global FULLTEXT_INDEX_MODE

        self.tablenames = ["fullsearchmeta", "searchmeta", "textsearchmeta"]
        self.db = sqlite.SQLiteConnector(config.get("paths.searchstore") + DB_NAME)

        self.schemafields = {}

        if option == "init":
            try:
                r = self.execute("select id from node where type='foobar'")
            except sqlite.OperationalError:
                createTables(self)
            except MySQLdb.ProgrammingError:
                createTables(self)

    def createTables(self):
        s = ''
        for i in range(1, MAX_SEARCH_FIELDS):
            s += 'field' + ustr(i) + ", "
        s = s[:-2]

        # simple search table
        self.db.execute('CREATE VIRTUAL TABLE fullsearchmeta USING fts3(id, type, schema, value)')
        # extended search table
        self.db.execute('CREATE VIRTUAL TABLE searchmeta USING fts3(id, type, schema, %s)' % (s))
        self.db.execute('CREATE VIRTUAL TABLE searchmeta_def USING fts3(name, position, attrname)')
        # fulltext search table
        self.db.execute('CREATE VIRTUAL TABLE textsearchmeta USING fts3(id, type, schema, value)')

    def getAllTableNames(self):
        ret = []
        for table in self.tablenames:
            ret.append(table)
            for table_add in ['content', 'segdir', 'segments']:
                ret.append(table + '_' + table_add)
        return ret

    def clearIndex(self):
        print "\nclearing index tables..."
        for table in self.getAllTableNames():
            try:
                self.db.execute("delete from " + table)
            except:
                print " - table", table, "not found"
        self.db.execute("DELETE FROM searchmeta_def")
        print "...cleared"

    def dropIndex(self):
        print "\ndropping index tables..."
        for table in self.getAllTableNames():
            try:
                self.db.execute("drop table " + table)
            except sqlite.OperationalError:
                print " - table", table, "not found"
        print "...dropped"

    def getDefForSchema(self, schema):
        ret = {}
        res = self.db.execute('SELECT position, attrname FROM searchmeta_def WHERE name="' + ustr(schema) + '" ORDER BY position')

        for id, attr in res:
            ret[id] = attr
        return ret

    def nodeToSimpleSearch(self, node):
        # build simple search index from node
        try:
            sql = 'INSERT INTO fullsearchmeta (id, type, schema, value) VALUES(\'{}\', \'{}\', \'{}\', \'{}| '.format(node.id,
                                                                                                                      node.getContentType(),
                                                                                                                      node.getSchema(),
                                                                                                                      node.name)

            # attributes
            a = ''
            for key, value in node.items():
                if key not in SYSTEMATTRS:
                    a += protect(u(value)) + '| '
            a = normalize_utf8(a)
            sql += a
            # files
            for file in node.getFiles():
                sql += protect(u(file.getName() + '| ' + file.getType() + '| ' + file.getMimeType()) + '| ')

            sql += '\')'
            self.db.execute(sql)
            return True
        except:
            return False

    def nodeToExtSearch(self, node):
        # build extended search index from node
        if len(node.getSearchFields()) == 0:
            # stop if schema has no searchfields
            return True

        v_list = {}
        i = 1
        for field in node.getSearchFields():
            v_list[ustr(i)] = node.get(field.getName())
            i += 1
        # save definition
        self.nodeToSchemaDef(node)

        sql = 'INSERT INTO searchmeta (id, type, schema, '
        values = ''
        try:
            if len(v_list) > 0:
                for key in v_list:
                    sql += 'field' + ustr(key) + ', '
                    #values += '"'+u(v_list[key])+ '", '
                    values += '"' + normalize_utf8(u(v_list[key])) + '", '
                sql = sql[:-2]
                values = values[:-2]
                sql = '{}) VALUES("{}", "{}", "{}", {})'.format(sql,
                                                                node.id,
                                                                node.getContentType(),
                                                                node.getSchema(),
                                                                values)
            else:
                sql = sql[:-2]
                sql = '{}) VALUES("{}", "{}", "{}")'.format(sql,
                                                            node.id,
                                                            node.getContentType(),
                                                            node.getSchema())
            self.db.execute(sql)
            return True
        except:
            return False

    def nodeToSchemaDef(self, node):
        fieldnames = {}
        i = 1
        for field in node.getSearchFields():
            fieldnames[ustr(i)] = field.getName()
            i += 1

        try:
            sql = 'DELETE FROM searchmeta_def WHERE name="' + node.getSchema() + '"'
            self.db.execute(sql)
        except:
            None
        for id in fieldnames.keys():
            sql = 'INSERT INTO searchmeta_def (name, position, attrname) VALUES("' + node.getSchema() + \
                '", "' + id + '", "' + fieldnames[id] + '")'
            self.db.execute(sql)

    """
        FULLTEXT_INDEX_MODE values:
            0: index fulltext without changes
            1: optimize fulltext (each word once)
            2: each word once with number of occurences
    """

    def nodeToFulltextSearch(self, node):
        # build fulltext index from node

        if not node.getContentType() in ("document", "dissertation"):
            # only build fulltext of document nodes
            # print "object is no document"
            return True
        r = re.compile("[a-zA-Z0-9]+")

        for file in node.getFiles():
            w = ''
            if file.getType() == "fulltext" and os.path.exists(file.retrieveFile()):
                data = {}
                content = ''
                with codecs.open(file.retrieveFile(), 'r', encoding='utf8') as f:
                    for line in f:
                        if FULLTEXT_INDEX_MODE == 0:
                            content += u(line)
                        else:
                            for w in re.findall(r, line):
                                if w not in data.keys():
                                    data[w] = 1
                            try:
                                data[w] += 1
                            except KeyError:
                                data[w] = 1

                if FULLTEXT_INDEX_MODE == 1:
                    for key in data.keys():
                        content += key + " "
                elif FULLTEXT_INDEX_MODE == 2:
                    for key in data.keys():
                        content += key + " [" + ustr(data[key]) + "] "
                sql = ""
                if len(content) > 0:
                    try:
                        sql = 'INSERT INTO textsearchmeta (id, type, schema, value) VALUES("{}", "{}", "{}", "{}")'.format(node.id,
                                                                                                                           node.getContentType(),
                                                                                                                           node.getSchema(),
                                                                                                                           iso2utf8(esc(content)))
                        self.db.execute(sql)
                    except:
                        print "error", node.id, "\n"
                        return False
                else:
                    print "no Content"
        return True

    def updateNode(self, node):
        self.removeNode(node)
        err = {}
        err['simple'] = []
        err['ext'] = []
        err['text'] = []
        err['commit'] = []

        if not self.nodeToSimpleSearch(node):
            err['simple'].append(node.id)
        if not self.nodeToExtSearch(node):
            err['ext'].append(node.id)
        if not self.nodeToFulltextSearch(node):
            err['text'].append(node.id)
        node.set("updatesearchindex", ustr(format_date()))
        return err

    def updateNodes(self, nodelist):
        print "\nupdating node index..."
        err = {}
        schemas = {}
        for node in nodelist:
            try:
                if node.getSchema() not in schemas.keys():
                    schemas[node.getSchema()] = node
                err = self.updateNode(node)
            except core.tree.NoSuchNodeError:
                print "error for id", node.id
        for key in schemas:
            self.nodeToSchemaDef(schemas[key])
        print "...finished"
        return err

    """
        mode:
            0: no printout
    """

    def removeNode(self, node, mode=0):
        for table in self.tablenames:
            try:
                self.db.execute('DELETE FROM {} WHERE id="{}"'.format(table,
                                                                      node.id))
            except:
                print "table", table, "does not exist"
        if mode != 0:
            print "node", node.id, "removed from index"

    def runIndexer(self, option=""):
        err = []
        root = tree.getRoot()
        if option != "":
            self.init(option)
        err = self.updateNodes(root.getAllChildren())
        print err

    def node_changed(self, node):
        self.updateNode(node)

searchIndexer = SearchIndexer()


def getIndexer():
    global searchIndexer
    return searchIndexer

if __name__ == "__main__":
    import time
    print "\nStart:", time.localtime(), "\n"
    searchIndexer.runIndexer(option="init")
    print "\nFinish:", time.localtime(), "\n"
