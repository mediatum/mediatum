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
import re
import os
import thread
import time
import codecs
import core
import core.config as config
import core.tree as tree
import logging
from utils.utils import u, union, normalize_utf8, OperationException, modify_tex
from utils.date import format_date
from math import ceil

import core.db.sqliteconnector as sqlite

logg = logging.getLogger(__name__)

DB_NAME_STD = 'searchindex.db'  # only 1 database
DB_NAME_FULL = 'searchindex_full.db'  # database for simple search
DB_NAME_EXT = 'searchindex_ext.db'  # database for extended search
DB_NAME_TEXT = 'searchindex_text.db'  # database for fulltext search
MAX_SEARCH_FIELDS = 32
SYSTEMATTRS = ['updateuser', 'updatetime', 'edit.lastmask', 'creationtime', 'creator']

"""
    0: index fulltext without changes
    1: optimize fulltext (each word once)
    2: each word once with number of occurences
"""
FULLTEXT_INDEX_MODE = 0
DBTYPE = config.get('database.searchdb', 'std')


class FtsSearcher:

    def __init__(self):
        self.connames = {'std': {'full': 'std', 'ext': 'std', 'text': 'std', 'std': 'std'},
                         'split': {'full': 'full', 'ext': 'ext', 'text': 'text'}}
        self.tablenames = {'full': "fullsearchmeta", 'ext': "searchmeta", 'text': "textsearchmeta"}
        self.schemas = list(set([schema[0].split('/')[1]
                                 for schema in
                                 tree.db.runQuery('''select distinct type
                                            from node
                                            where type
                                            like "%%/%%"''')]))
        self.db = {}

        if DBTYPE not in self.connames.keys():
            raise OperationException("error in search definition")

        # fills in db with key {schema}_{dbtype}: sqliteconnector
        for schema in self.schemas:
            for conname in self.connames[DBTYPE]:
                self.addDB(schema, conname)

        self.normalization_items = None

    def run_search(self, field, op, value):

        def getSQL(type, value, spc={}):  # deliver sql for given type
            value = normalize_utf8(protect(u(value)))

            if type == "full":  # all metadata
                return 'select distinct(id) from fullsearchmeta where fullsearchmeta match \'value:' + value + '\' and type <>\'directory\''
            elif type == "fulltext":  # fulltext
                return 'select distinct(id) from textsearchmeta where textsearchmeta match \'value:' + value + '\' and type<>\'directory\''
            elif type == "schema":  # schemadef
                return 'select distinct(id) from fullsearchmeta where schema="' + value.replace("'", "") + '"'
            elif type == "objtype":  # object type
                return 'select distinct(id) from fullsearchmeta where type="' + value.replace("'", "") + '"'
            elif type == "updatetime":  # update time with operator <|>|=
                if len(value) == 10:
                    value += "T00:00:00"
                return 'select distinct(id) from searchmeta where updatetime ' + spc['op'] + ' "' + value.replace("t", "T") + '"'
            elif type == "field":
                return 'select position, name from searchmeta_def where attrname=\'' + value + '\''
            elif type == "spcompare":
                return 'select distinct(id) from searchmeta where schema="' + \
                    ustr(spc['pos'][1]) + '" and field' + ustr(spc['pos'][0]) + ' ' + spc['op'] + ' "' + value + '"'
            elif type == "spfield":
                return 'select distinct(id) from searchmeta where field' + ustr(spc['pos'][0]) + '=""'
            elif type == "spmatch":
                return 'select distinct(id) from searchmeta where schema=\'' + \
                    ustr(spc['pos'][1]) + '\' and field' + ustr(spc['pos'][0]) + ' match \'' + value + '\''
            elif type == "content_full":
                return 'select * from fullsearchmeta where id=\'' + value + '\''
            elif type == "content_text":
                return 'select * from textsearchmeta where id=\'' + value + '\''
            elif type == "content_ext":
                return 'select * from searchmeta where id=\'' + value + '\''

        ret = []
        if value == "" or field == "" or op == "":
            return []

        for schema in self.schemas:
            if field == "full":  # all metadata incl. fulltext
                res1 = self.execute(getSQL("full", value), schema, 'full')  # all metadata
                res2 = self.execute(getSQL("fulltext", value), schema, 'text')  # fulltext
                ret += union([[ustr(s[0]) for s in res1], [ustr(s[0]) for s in res2]])

            elif field == "fulltext":  # fulltext
                ret += [ustr(s[0]) for s in self.execute(getSQL("fulltext", value),
                                                        schema,
                                                        'text')]

            elif field == "allmetadata":  # all metadata
                ret += [ustr(s[0]) for s in self.execute(getSQL("full", value),
                                                        schema,
                                                        'full')]

            elif field == "schema":
                ret += [ustr(s[0]) for s in self.execute(getSQL("schema", value),
                                                        schema,
                                                        'full')]

            elif field == "objtype":
                ret += [ustr(s[0]) for s in self.execute(getSQL("objtype", value),
                                                        schema,
                                                        'full')]

            elif field == "updatetime":
                ret += [ustr(s[0]) for s in self.execute(getSQL("updatetime", value, spc={'op': op}),
                                                        schema,
                                                        'full')]

            elif field == "searchcontent":
                ret = [[], [], []]
                for item in self.execute(getSQL("content_full", value), schema, 'full'):  # value = id
                    ret[0] += [i for i in item if i]
                for item in self.execute(getSQL("content_ext", value), schema, 'ext'):
                    ret[1] += [i for i in item if i]
                for item in self.execute(getSQL("content_text", value), schema, 'text'):  # value = id
                    ret[2] += [i for i in item if i]
                ret += ret

            else:  # special search
                for pos in self.execute(getSQL("field", field), schema, self.connames[DBTYPE]['ext']):
                    if op in [">=", "<="]:
                        res = self.execute(getSQL("spcompare", value, spc={'op': op, 'pos': pos}), schema, 'ext')
                    else:
                        if value == "''":
                            res = self.execute(getSQL("spfield", '', spc={'pos': pos}), schema, 'ext')
                        else:
                            res = self.execute(getSQL("spmatch", value, spc={'pos': pos}), schema, 'ext')

                    res = [ustr(s[0]) for s in res]
                    if len(ret) == 0:
                        ret += res

                    if len(res) > 0:
                        ret += union([ret, res])
        return ret

    def query(self, q=""):
        from core.tree import searchParser
        p = searchParser.parse(q)
        return p.execute()

    def addDB(self, schema, connection_name):
        if '_'.join([schema, self.connames[DBTYPE][connection_name]]) not in self.db.keys():
            self.db['_'.join([schema, self.connames[DBTYPE][connection_name]])] = \
                sqlite.SQLiteConnector("%s%s_%s" % (config.get("paths.searchstore"),
                                                    schema,
                                                    eval('DB_NAME_' + (self.connames[DBTYPE][connection_name])
                                                         .upper())))

    def initIndexer(self, option="", new_schema=""):
        def create(sql, schema, _type):
            try:
                self.execute(sql, schema, _type)
            except:
                e = sys.exc_info()[1]
                if "already exists" not in ustr(e):
                    raise

        def createDB(schema):
            create('CREATE VIRTUAL TABLE fullsearchmeta USING fts3(id, type, schema, value)',
                   schema,
                   'full')

            # extended search table
            create('CREATE VIRTUAL TABLE searchmeta USING fts3(id, type, schema, updatetime, ' +
                   ", ".join(['field' + ustr(i) for i in range(1, MAX_SEARCH_FIELDS)]) + ')', schema, 'ext')
            create('CREATE VIRTUAL TABLE searchmeta_def USING fts3(name, position, attrname)',
                   schema,
                   'ext')

            # fulltext search table
            create('CREATE VIRTUAL TABLE textsearchmeta USING fts3(id, type, schema, value)',
                   schema,
                   'text')

        if option == 'init':
            for schema in self.schemas:
                createDB(schema)

        if new_schema != '':
            createDB(new_schema)

    def addSchema(self, schema):
        if schema not in self.schemas:
            self.schemas.append(schema)
            for conname in self.connames[DBTYPE]:
                self.addDB(schema, conname)
            self.initIndexer(new_schema=schema)
        else:
            print 'search db already exists'

    def getAllTableNames(self):
        ret = {'full': [], 'ext': [], 'text': []}
        for type in self.tablenames:
            ret.append(self.tablenames[type])
            for table_add in ['content', 'segdir', 'segments']:
                ret.append(self.tablenames[type] + '_' + table_add)
        return ret

    def clearIndex(self):
        print "\nclearing index tables..."
        all_tables = self.getAllTableNames()
        for type in all_tables:
            for table in all_tables[type]:
                try:
                    self.execute('DELETE FROM ' + table, type)
                except:
                    pass
        try:
            self.execute('DELETE FROM searchmeta_def', 'ext')
        except:
            pass
        print "...cleared"

    def dropIndex(self):
        print "\ndropping index tables..."
        all_tables = self.getAllTableNames()
        for type in all_tables:
            for table in all_tables[type]:
                try:
                    self.execute('DROP TABLE ' + table, type)
                except:
                    pass
        try:
            self.execute('DROP TABLE searchmeta_def', 'ext')
        except:
            pass
        print "...dropped"

    def getDefForSchema(self, schema):
        ret = {}
        res = self.execute(u'SELECT position, attrname FROM searchmeta_def WHERE name="{}" ORDER BY position'.format(schema), 'ext') or []
        for id, attr in res:
            ret[id] = attr
        return ret

    def execute(self, sql, schema, _type='std'):
        try:
            return self.db['_'.join([schema, self.connames[DBTYPE][_type]])].execute(sql)
        except Exception:
            print "error in search indexer operation", sql, schema

    def getNodeInformation(self):
        ret = {}
        res = self.execute('SELECT distinct(id) FROM fullsearchmeta ORDER BY id', 'full')
        ret['full'] = [s[0] for s in res]

        res = self.execute('SELECT distinct(id) FROM searchmeta ORDER BY id', 'ext')
        ret['ext'] = [s[0] for s in res]

        res = self.execute('SELECT distinct(id) FROM textsearchmeta ORDER BY id', 'text')
        ret['text'] = [s[0] for s in res]

        return ret

    def nodeToSimpleSearch(self, node, schema, type=""):  # build simple search index from node

        sql_upd =u"UPDATE fullsearchmeta SET type='{}', schema='{}', value='{}| ".format(node.getContentType(),
                                                                                        node.getSchema(),
                                                                                        node.name)
        sql_ins = u"INSERT INTO fullsearchmeta (id, type, schema, value) VALUES('{}', '{}', '{}', '{}| ".format(node.id,
                                                                                                               node.getContentType(),
                                                                                                               node.getSchema(),
                                                                                                               node.name)

        # attributes
        val = ''
        for key, value in node.items():
            if key not in SYSTEMATTRS:  # ignore system attributes
                val += protect(u(value)) + '| '
        for v in val.split(" "):
            v = u(v)
            if normalize_utf8(v) != v.lower():
                val += ' ' + normalize_utf8(v)

        val = val.replace(chr(0), "") + ' '

        # remove tex markup
        val = modify_tex(val, 'strip')

        # files
        for file in node.getFiles():
            val += protect(u(file.getName() + '| ' + file.getType() + '| ' + file.getMimeType()) + '| ')

        sql_upd += val + u'\' WHERE id=\'{}\''.format(node.id)
        sql_ins += val + '\')'

        sql = ""
        try:
            sql = u'SELECT id from fullsearchmeta WHERE id=\'{}\''.format(node.id)
            if self.execute(sql, schema, 'full'):  # check existance
                sql = sql_upd  # do update
            else:
                sql = sql_ins  # do insert
            self.execute(sql, schema, 'full')
            return True
        except:
            logg.exception('error in sqlite insert/update: %s', sql)
            return False

    def nodeToExtSearch(self, node, schema):  # build extended search index from node

        if len(node.getSearchFields()) == 0:  # stop if schema has no searchfields
            return True

        self.nodeToSchemaDef(node, schema)  # save definition

        keyvalue = []
        i = 1
        for field in node.getSearchFields():
            key = "field%d" % i
            i += 1
            value = ""
            if field.getFieldtype() == "union":
                for item in field.get("valuelist").split(";"):
                    value += node.get(item) + '|'
            else:
                value = node.get(field.getName())
            keyvalue += [(key, modify_tex(u(protect(value)), 'strip'))]

        sql0 = u'SELECT id FROM searchmeta where id=\'{}\''.format(node.id)
        sql1 = 'UPDATE searchmeta SET '
        sql2 = 'INSERT INTO searchmeta (id, type, schema, updatetime'
        for key, value in keyvalue:
            sql1 += key + "='" + normalize_utf8(value) + "', "
            sql2 += ", "
            sql2 += key
        sql1 += "type='" + node.getContentType() + "', schema='" + schema + "', updatetime='" + node.get("updatetime") + "'"
        sql2 += ") VALUES("
        sql2 += u'\'{}\', "{}", "{}", "{}"'.format(node.id,
                                            node.getContentType(),
                                            schema,
                                            node.get("updatetime"))

        for key, value in keyvalue:
            sql2 += ", '" + normalize_utf8(value) + "'"
        sql1 += u" WHERE id='{}'".format(node.id)
        sql2 += ")"

        sql = ""
        try:
            sql = sql0
            if self.execute(sql0, schema, 'ext'):  # select
                sql = sql1
                self.execute(sql1, schema, 'ext')  # do update
            else:
                sql = sql2
                self.execute(sql2, schema, 'ext')  # do insert
            return True
        except:
            logg.exception('error in sqlite insert/update: %s', sql)
            return False

    def nodeToSchemaDef(self, node, schema):  # update schema definition
        fieldnames = {}
        i = 1
        for field in node.getSearchFields():
            fieldnames[ustr(i)] = field.getName()
            i += 1
        self.execute('DELETE FROM searchmeta_def WHERE name="' + schema + '"',
                     schema,
                     'ext')
        for id in fieldnames.keys():
            self.execute(
                'INSERT INTO searchmeta_def (name, position, attrname) VALUES("' +
                schema +
                '", "' +
                id +
                '", "' +
                fieldnames[id] +
                '")',
                schema,
                'ext')

    def nodeToFulltextSearch(self, node, schema):  # build fulltext index from node

        if not hasattr(node, "getCategoryName") or not node.getCategoryName() == "document":  # only build fulltext of document nodes
            return True
        r = re.compile("[a-zA-Z0-9]+")

        if self.execute(u'SELECT id from textsearchmeta where id=\'{}\''.format(node.id), schema, 'text'):
            # FIXME: we should not delete the old textdata from this node, and insert
            # the new files. Only problem is, DELETE from a FTS3 table is prohibitively
            # slow.
            return

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

                content = u(content.replace("'", "").replace('"', ""))
                if len(content) > 0:
                    content_len = len(content)
                    p = 0

                    while p in range(0, int(ceil(content_len / 500000.0))):
                        sql = u'INSERT INTO textsearchmeta (id, type, schema, value) VALUES("{}", "{}", "{}", "{}")'.format(node.id,
                                                                                                                     node.getContentType(),
                                                                                                                     schema,
                                                                                                                     normalize_utf8((content[p * 500000:(p + 1) * 500000 - 1])))
                        try:
                            self.execute(sql, schema, 'text')
                        except:
                            print "\nerror in fulltext of node", node.id
                            return False
                        p += 1
                return True
        return True

    def updateNodeIndex(self, node, schema):
        err = {}
        err['simple'] = []
        err['ext'] = []
        err['text'] = []
        err['commit'] = []

        if not self.nodeToSimpleSearch(node, schema):
            err['simple'].append(node.id)
        if not self.nodeToExtSearch(node, schema):
            err['ext'].append(node.id)
        if not self.nodeToFulltextSearch(node, schema):
            err['text'].append(node.id)

        node.set("updatesearchindex", ustr(format_date()))
        return err

    def updateNodesIndex(self, nodelist):
        print "updating node index for", len(nodelist), "nodes..."

        err = {}
        schemas = {}

        #t1 = time.time()
        for node in nodelist:
            try:
                schema = node.getSchema()
                if schema not in schemas.keys():
                    schemas[schema] = node
                if schema not in self.schemas:
                    self.addSchema(schema)
                err = self.updateNodeIndex(node, schema)
            except core.tree.NoSuchNodeError:
                # we ignore this exception, and mark the node
                # non-dirty anyway, to prevent it from blocking
                # updates of other nodes
                logg.exception("error during updating %s", node.id)
            node.cleanDirty()

        for key in schemas:
            self.nodeToSchemaDef(schemas[key], key)

        return err

    """
        mode:
            0: no printout
    """

    def removeNodeIndex(self, node):
        for _type in self.tablenames:
            try:
                self.execute('DELETE FROM %s WHERE id="%s"' % (self.tablenames[_type],
                                                               node.id),
                             node.getSchema(),
                             _type)
                print 'node %s removed from index %s %s' % (ustr(node.id), node.getSchema(), _type)
            except Exception as e:
                print e

    def reindex(self, nodelist):
        for node in nodelist:
            node.setDirty()

    def node_changed(self, node):
        print "node_change fts3", node.id
        node.setDirty()

    def getSearchInfo(self):
        ret = []
        key = ["sqlite_type", "sqlite_name", "sqlite_tbl_name", "sqlite_rootpage", "sqlite_sql"]
        for type in self.connames[DBTYPE]:
            for table in self.execute("SELECT * FROM sqlite_master", type):
                i = 0
                t = []
                for item in table:
                    t.append((key[i], item))
                    i += 1
                if t[0][1] == "table":
                    items = self.execute("SELECT count(*) FROM " + t[2][1], type)
                    for item in items:
                        t.append(("sqplite_items_count", ustr(item[0])))
                ret.append(t)
        return ret

    def getSearchSize(self):
        import os
        return os.stat(config.settings["paths.searchstore"] + "searchindex.db")[6]

ftsSearcher = FtsSearcher()
ftsSearcher.initIndexer()


def protect(s):
    return s.replace('\'', '"')


def subnodes(node):
    return node.getAllChildren().getIDs()


def fts_indexer_thread():
    if not time:
        return
    while True:
        time.sleep(3)
        dirty = tree.getDirtySchemaNodes(10)
        if dirty:
            ftsSearcher.updateNodesIndex(dirty)


def startThread():
    thread_id = thread.start_new_thread(fts_indexer_thread, ())
