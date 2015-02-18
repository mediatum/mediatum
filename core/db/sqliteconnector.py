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

import os
import sys
import logging
import thread
import core.config as config
import codecs

from .connector import Connector


logg = logging.getLogger(__name__)


SQLITE_API = None

if not SQLITE_API:
    try:
        import sqlite3 as _test_sqlite
        con = _test_sqlite.connect(":memory:")
        con.execute("create virtual table t using fts3(a, b)")
        SQLITE_API = "sqlite3"
    except:
        try:
            from pysqlite2 import dbapi2 as _test_sqlite
            con = _test_sqlite.connect(":memory:")
            con.execute("create virtual table t using fts3(a, b)")
            SQLITE_API = "pysqlite2"
        except:
            logg.warn('Warning: no fts3 enabled for sqlite connector')

if SQLITE_API == 'sqlite3':
    import sqlite3 as sqlite
    logg.info('using fts3 enabled module sqlite3')
elif SQLITE_API == 'pysqlite2':
    from pysqlite2 import dbapi2 as sqlite
    logg.info("using fts3 enabled module pysqlite2")
else:
    try:
        import sqlite3 as sqlite
    except:
        from pysqlite2 import dbapi2 as sqlite

from core.db.database import initDatabaseValues
from utils import *

if __name__ == "__main__":
    sys.path += [".."]

debug = 0
log = logg = logging.getLogger(__name__)

sqlite_lock = thread.allocate_lock()


class SQLiteConnector(Connector):

    def __init__(self, db=None):
        if db is None:
            if not os.path.exists(config.get("paths.datadir") + "db/imagearch.db"):
                try:
                    os.makedirs(os.path.dirname(config.get("paths.datadir") + "db/"))
                except OSError:
                    pass
            self.db = config.get("paths.datadir") + "db/imagearch.db"
            self.isInitialized()
        else:
            self.db = db

    def applyPatches(self):
        self.runQueryNoError("alter table node add column ([localread] TEXT NULL)")

    def isInitialized(self):
        try:
            v = self.execute("select id from node where type='root'")
            v[0]
            return True
        except sqlite.OperationalError:
            self.createTables()
            initDatabaseValues(self)
        except IndexError:
            initDatabaseValues(self)
        return False

    def esc(self, text):
        return "'" + text.replace("'", "\\'") + "'"

    def close(self):
        pass

    def execute(self, sql, obj=None):
        sqlite_lock.acquire()
        try:
            if not os.path.exists(config.get("paths.tempdir")):
                os.makedirs(os.path.dirname(config.get("paths.tempdir")))
            with codecs.open(config.get("paths.tempdir") + "sqlite.log", "ab+", encoding='utf8') as fi:
                fi.write(sql + "\n")

            con = sqlite.connect(self.db, check_same_thread=True)
            con.text_factory = type("")
            cur = con.cursor()
            if obj:
                res = cur.execute(sql, obj)
            else:
                res = cur.execute(sql)
            s = res.fetchall()
            cur.close()
            con.commit()
            con.close()
            return s
        except sqlite.OperationalError as e:
            logg.error("execute() failed for statement '%s'", sql, exc_info=1)
            raise
        finally:
            sqlite_lock.release()

    def runQuery(self, sql, obj=None):
        if debug:
            log.debug(sql)
        return self.execute(sql, obj)

    def runQueryNoError(self, sql, obj=None):
        try:
            return self.execute(sql, obj)
        except:
            log.debug(sql)

    def createTables(self):
        self.runQueryNoError(
            "CREATE TABLE [nodeaccess] ([name] VARCHAR(64)  NOT NULL PRIMARY KEY, [description] TEXT  NULL,[rule] TEXT  NULL)")
        self.runQueryNoError(
            "CREATE TABLE [node] ([id] INTEGER  NOT NULL PRIMARY KEY AUTOINCREMENT, [name] VARCHAR(255)  NULL, [type] VARCHAR(32)  NULL, [readaccess] TEXT  NULL, [writeaccess] TEXT  NULL, [dataaccess] TEXT  NULL, [lastchange] DATE DEFAULT CURRENT_DATE NULL, [orderpos] INTEGER DEFAULT '1' NULL, [dirty] INTEGER DEFAULT '0', [localread] TEXT NULL)")
        self.runQueryNoError(
            "CREATE TABLE [nodeattribute] ([nid] INTEGER DEFAULT '0' NOT NULL, [name] VARCHAR(50)  NOT NULL, [value] TEXT  NULL)")
        self.runQueryNoError(
            "CREATE TABLE [nodefile] ([nid] INTEGER DEFAULT '0' NOT NULL, [filename] TEXT  NOT NULL, [type] VARCHAR(32)  NOT NULL, [mimetype] VARCHAR(32)  NULL)")
        self.runQueryNoError("CREATE TABLE [nodemapping] ([nid] INTEGER DEFAULT '0' NOT NULL, [cid] INTEGER DEFAULT '0' NOT NULL)")
        self.runQueryNoError(
            "CREATE OR REPLACE VIEW contaermapping AS select nodemapping.nid AS nid`,`nodemapping`.`cid` AS `cid`,`node`.`type` AS `type` from (`nodemapping` join `node` on((`nodemapping`.`cid` = `node`.`id`))) where (locate('/',`node`.`type`) = 0)")
        self.runQueryNoError(
            "CREATE OR REPLACE VIEW contentmapping AS select nodemapping.nid AS `id`,`nodemapping`.`cid` AS `cid`,`node`.`type` AS `type` from (`nodemapping` join `node` on((`nodemapping`.`cid` = `node`.`id`))) where (locate('/',`node`.`type`) > 0)")

        self.runQueryNoError("CREATE VIEW containermapping AS select nodemapping.nid AS nid, nodemapping.cid AS cid,node.type AS type\
        FROM (nodemapping join node on((nodemapping.cid = node.id))) where (instr(node.type, '/') = 0);")
        self.runQueryNoError("CREATE VIEW contentmapping AS select nodemapping.nid AS nid, nodemapping.cid AS cid,node.type AS type\
        FROM (nodemapping join node on((nodemapping.cid = node.id))) where (instr(node.type, '/') > 0);")

        self.runQueryNoError("CREATE INDEX [IDX_NODE_ID] ON [node]([id]  ASC)")
        self.runQueryNoError("CREATE INDEX [IDX_NODE_TYPE] ON [node]([type]  ASC)")
        self.runQueryNoError("CREATE INDEX [IDX_NODE_ORDERPOS] ON [node]([orderpos]  ASC)")
        self.runQueryNoError("CREATE INDEX [IDX_NODE_NAME] ON [node]([name]  ASC)")
        self.runQueryNoError("CREATE INDEX [IDX_NODEATTRIBUTE_NID] ON [nodeattribute]([nid]  ASC)")
        self.runQueryNoError("CREATE INDEX [IDX_NODEATTRIBUTE_NIDNAME] ON [nodeattribute]([nid]  ASC,[name]  ASC)")
        self.runQueryNoError("CREATE INDEX [IDX_NODEATTRIBUTE_NAME] ON [nodeattribute]([name]  ASC)")
        self.runQueryNoError("CREATE INDEX [IDX_NODEFILE_NID] ON [nodefile]([nid]  ASC)")
        self.runQueryNoError("CREATE INDEX [IDX_NODEMAPPING_NID] ON [nodemapping]([nid]  ASC)")
        self.runQueryNoError("CREATE INDEX [IDX_NODEMAPPING_CID] ON [nodemapping]([cid]  ASC)")
        self.runQueryNoError("CREATE INDEX [IDX_NODEMAPPING_NIDCID] ON [nodemapping]([nid]  ASC,[cid]  ASC)")
        # self.commit()

    def dropTables(self):
        self.runQueryNoError("drop table nodeaccess")
        self.runQueryNoError("drop table user")
        self.runQueryNoError("drop table node")
        self.runQueryNoError("drop table nodefile")
        self.runQueryNoError("drop table nodeattribute")
        self.runQueryNoError("drop table nodemapping")
        # self.commit()
        log.info("tables deleted")

    def clearTables(self):
        self.runQueryNoError("delete from nodeaccess")
        self.runQueryNoError("delete from user")
        self.runQueryNoError("delete from node")
        self.runQueryNoError("delete from nodefile")
        self.runQueryNoError("delete from nodeattribute")
        self.runQueryNoError("delete from nodemapping")
        # self.commit()
        log.info("tables cleared")

    def getRule(self, name):
        rule = self.runQuery("select name, description, rule from nodeaccess where name=" + self.esc(name))
        if len(rule) == 1:
            return rule[0][2], rule[0][1]
        elif len(rule) > 1:
            raise Exception("DuplicateRuleError")
        else:
            raise Exception("RuleNotFoundError")

    def getRuleList(self):
        return self.runQuery("select name, description, rule from nodeaccess order by name")

    def updateRule(self, rule, oldname):
        # try:
        sql = "update nodeaccess set rule='" + \
            rule.getRuleStr() + "', description='" + rule.getDescription() + "' where name='" + oldname + "'"
        self.runQuery(sql)
        return True
        # except:
        #    return False

    def addRule(self, rule):
        try:
            self.runQuery("insert into nodeaccess (name, rule, description) values('" + rule.getName() +
                          "', '" + rule.getRuleStr() + "', '" + rule.getDescription() + "')")
            return True
        except:
            return False

    def deleteRule(self, name):
        try:
            self.runQuery("delete from nodeaccess where name='" + name + "'")
            return True
        except:
            return False

    def getAllDBRuleNames(self):
        ret = {}
        for field in ["readaccess", "writeaccess", "dataaccess"]:
            for names in self.runQuery('select distinct(' + field + ') from node where ' + field + ' not like "{%"'):
                rules = names[0].split(",")
                for rule in rules:
                    if rule != "":
                        ret[rule] = ""
        return ret.keys()

    def ruleUsage(self, rulename):
        result = self.runQuery('select count(*) from node where readaccess="' + rulename +
                               '" or writeaccess="' + rulename + '" or dataaccess="' + rulename + '"')
        return int(result[0][0])

    def resetNodeRule(self, rulename):
        for field in ["readaccess", "writeaccess", "dataaccess"]:
            self.runQuery('update node set ' + field + '="" where ' + field + '="' + rulename + '"')

    """ node section """

    def createNode(self, name, type):
        orderpos = self.mkOrderPos()
        id = self.mkID()
        self.runQuery("insert into node (id,name,type,orderpos) values(?,?,?,?)", (id, name, type, orderpos))
        res = self.runQuery("select max(id) from node")
        return ustr(res[0][0])

    def addChild(self, nodeid, childid, check=1):
        if check:
            if childid == nodeid:
                raise ValueError("Tried to add node " + nodeid + " to itself as child")
            # does this child already exist?
            t = self.runQuery("select count(*) as num from nodemapping where nid=" + nodeid + " and cid=" + childid)
            if t[0][0] > 0:
                return
        self.setNodeOrderPos(childid, self.mkOrderPos())
        self.runQuery("insert into nodemapping (nid, cid) values(?,?)", (nodeid, childid))

    def setAttribute(self, nodeid, attname, attvalue, check=1):
        if attvalue is None:
            raise TypeError("Attribute value is None")
        if check:
            t = self.runQuery("select count(*) as num from nodeattribute where nid=" + nodeid + " and name='" + attname + "'")
            if len(t) > 0 and t[0][0] > 0:
                self.runQuery("update nodeattribute set value='" + ustr(attvalue) + "' where nid=" + nodeid + " and name='" + attname + "'")
                return
        self.runQuery("insert into nodeattribute (nid, name, value) values(?,?,?)", (nodeid, attname, ustr(attvalue)))

    def addFile(self, nodeid, path, type, mimetype):
        self.runQuery("insert into nodefile (nid, filename, type, mimetype) values(?,?,?,?)", (nodeid, path, type, mimetype))

    def getStatus(self):
        ret = []
        key = ["sqlite_type", "sqlite_name", "sqlite_tbl_name", "sqlite_rootpage", "sqlite_sql"]
        for table in self.runQuery("select * from sqlite_master"):
            i = 0
            t = []
            for item in table:
                t.append((key[i], item))
                i += 1

            items = []
            try:
                items = self.runQuery("select * from sqlite_stat1 where tbl='" + t[2][1] + "'")
            except:
                pass
            if len(items) > 0:
                t.append(("sqplite_items_count", ustr(items[0][2]).split(" ")[0]))

            ret.append(t)

        return ret

    def getDBSize(self):
        import os
        return os.stat(config.get("paths.datadir") + "db/imagearch.db")[6]

    def sort_nodes_by_fields(self, nids, fields):
        """Sorts nodes by field (attribute) values.
        :param nids: node ids (ignored)
        :param fields: field names to sort for. Prepend - to sort descending
        :return: all ordered node ids which have an attr called fields[0]
        """
        q = "SELECT nid from {} " \
            "WHERE {} " \
            "ORDER BY {};"

        join_parts = []
        where_name_parts = []
        order_parts = []

        for i, f in enumerate(fields):
            alias = "a" + ustr(i)
            if i > 0:
                join_parts.append("nodeattribute AS " + alias)
            fname, direction = self._sql_sort_field_name_and_dir(f)
            where_name_parts.append("{}.name={}".format(alias, fname))
            order_parts.append("{}.value{}".format(alias, direction))

        # looks like nodeattribute as a0 INNER JOIN nodeattribute as a1 USING (nid) INNER JOIN ...
        if len(fields) > 1:
            join_clause = "nodeattribute as a0 INNER JOIN " + "INNER JOIN".join(j + " USING (nid)" for j in join_parts)
        else:
            join_clause = "nodeattribute as a0"
        where_name_clause = " AND ".join(where_name_parts)
        order_clause = ", ".join(order_parts)
        query = q.format(join_clause, where_name_clause, order_clause)
        return [ustr(r[0]) for r in self.runQuery(query)]
