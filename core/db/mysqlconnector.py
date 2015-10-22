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
import MySQLdb
import sys
from time import *
import logging
import thread
import msgpack
from .connector import Connector

from core.db.database import initDatabaseValues, DatabaseException

if __name__ == "__main__":
    sys.path += [".."]

import core.config as config
from utils.utils import *

debug = 0
debug_ignore_statements_re = None

log = logging.getLogger('database')


class MYSQLConnector(Connector):

    def __init__(self):
        self.dbhost = config.get("database.dbhost", "localhost")
        self.dbport = int(config.get("database.dbport", "3306"))
        self.database = config.get("database.db", "mediatum")
        self.user = config.get("database.user", "mediatumadmin")
        self.passwd = config.get("database.passwd", "")
        self.charset = config.get("database.charset", "")

        self.db = MySQLdb.connect(host=self.dbhost, port=self.dbport, user=self.user, passwd=self.passwd, db=self.database, charset=self.charset)
        self.dblock = thread.allocate_lock()
        self.nodes = {}

        function = str(traceback.extract_stack()[-2][0]) + ":" + str(traceback.extract_stack()[-2][2])
        log.info("Connecting to [" + self.user + "@" + self.database + "] " + function)

        # test base table
        try:
            r = self.runQuery("select id from node where type='root'")
            r[0]
        except MySQLdb.ProgrammingError:
            self.createTables()
            initDatabaseValues(self)
        except IndexError:
            initDatabaseValues(self)

        # test for mapping views
        try:
            r = self.runQuery("select nid from containermapping limit 1")
            r[0]
        except MySQLdb.ProgrammingError:
            self.runQueryNoError(
                "CREATE OR REPLACE VIEW `containermapping` AS select `nodemapping`.`nid` AS `nid`,`nodemapping`.`cid` AS `cid`,`node`.`type` AS `type` from (`nodemapping` join `node` on((`nodemapping`.`cid` = `node`.`id`))) where (locate('/',`node`.`type`) = 0)")
            self.runQueryNoError(
                "CREATE OR REPLACE VIEW `contentmapping` AS select `nodemapping`.`nid` AS `nid`,`nodemapping`.`cid` AS `cid`,`node`.`type` AS `type` from (`nodemapping` join `node` on((`nodemapping`.`cid` = `node`.`id`))) where (locate('/',`node`.`type`) > 0)")

        # test for nodetree views
        try:
            r = self.runQuery("select nid01 from nodetree limit 1")
            r[0]
        except MySQLdb.ProgrammingError:
            self.runQueryNoError("""
CREATE OR REPLACE VIEW `nodetree` AS
SELECT m01.`cid` AS `nid01`,
       m02.`cid` AS `nid02`,
       m03.`cid` AS `nid03`,
       m04.`cid` AS `nid04`,
       m05.`cid` AS `nid05`,
       m06.`cid` AS `nid06`,
       m07.`cid` AS `nid07`,
       m08.`cid` AS `nid08`,
       m09.`cid` AS `nid09`,
       m10.`cid` AS `nid10`
FROM `nodemapping` m01
LEFT OUTER JOIN `nodemapping` m02 ON m01.`cid` = m02.`nid`
LEFT OUTER JOIN `nodemapping` m03 ON m02.`cid` = m03.`nid`
LEFT OUTER JOIN `nodemapping` m04 ON m03.`cid` = m04.`nid`
LEFT OUTER JOIN `nodemapping` m05 ON m04.`cid` = m05.`nid`
LEFT OUTER JOIN `nodemapping` m06 ON m05.`cid` = m06.`nid`
LEFT OUTER JOIN `nodemapping` m07 ON m06.`cid` = m07.`nid`
LEFT OUTER JOIN `nodemapping` m08 ON m07.`cid` = m08.`nid`
LEFT OUTER JOIN `nodemapping` m09 ON m08.`cid` = m09.`nid`
LEFT OUTER JOIN `nodemapping` m10 ON m09.`cid` = m10.`nid`""")

        try:
            r = self.runQuery("select * from node where dirty=1 limit 1")
        except MySQLdb.OperationalError:
            self.runQuery("alter table node add column dirty bool")

    def applyPatches(self):
        self.runQueryNoError("alter table node add column (localread TEXT NULL)")

    def close(self):
        self.dblock.acquire()
        try:
            try:
                self.db.close()
            except:
                pass
        finally:
            self.dblock.release()

    def _reconnect(self):
        ok = 0
        try:
            if self.db:
                # self.db.ping()
                ok = 1
        except MySQLdb.OperationalError as nr:
            ok = 0
            log.warning("Pinging failed (" + str(nr) + ")... reconnecting to [" + self.user + "@" + self.database + "]")
            self.db = None

        if not ok:
            self.db = MySQLdb.connect(host=self.dbhost, user=self.user, passwd=self.passwd, db=self.database)
        return self.db

    def esc(self, s):
        if isinstance(s, unicode):
            s = s.encode("utf8")
        try:
            return self.db.escape(s)
        except:
            try:
                return MySQLdb.escape(s, self.db.converter)
            except:
                # TODO: this should not be necessary.
                # maybe switch to
                #       cursor.execute("select whatever from whomever where something = %s", my_parameter)
                #?
                s = str(s)
                return "'" + s.replace('\\', '\\\\').replace('"', '\\"').replace('\'', '\\\'') + "'"

    def execute(self, sql, params=None, log_errors=True):
        self.dblock.acquire()
        try:
            while True:
                try:
                    self._reconnect()
                    c = self.db.cursor()
                    c.execute(sql, params)
                    result = c.fetchall()
                    c.close()
                    self.db.commit()
                    return result
                except MySQLdb.Error as nr:
                    def log_sql_error(msg, exc_info=0):
                        if log_errors:
                            log.error(msg + " while executing SQL '%s', params %s", sql, params, exc_info=exc_info)

                    if nr[0] == 2002:
                        log_sql_error("can't connect to sql server")
                        self.db = None
                        sleep(5)
                    elif nr[0] == 2006:
                        log_sql_error("mysql server has gone away")
                        self.db = None
                        sleep(5)
                    elif nr[0] == 2013:
                        log_sql_error("lost connection to database")
                        self.db = None
                        sleep(5)
                    else:
                        log_sql_error("", exc_info=1)
                        raise
                except:
                    log.error("non-MySQL error while executing SQL '%s', params %s", sql, params, exc_info=1)
                    raise

        finally:
            self.dblock.release()

    def runQuery(self, sql, *args, **kwargs):
        if args and kwargs:
            raise Exception("only positional or named parameters allowed, not both!")
        params = args or kwargs or None
        if debug:
            if not debug_ignore_statements_re or not debug_ignore_statements_re.match(sql):
                print "SQL echo:", sql, ", params", params
        result = self.execute(sql, params)
        return result

    def runQueryNoError(self, sql):
        if debug:
            log.debug(sql)
        try:
            return self.execute(sql, log_errors=False)
        except MySQLdb.OperationalError as nr:
            if nr[0] == 1050:
                log.info("table already exists: " + sql)
                return None
            elif nr[0] == 1051:
                log.info("table doesn't exists: " + sql)
                return None
            elif nr[0] == 1060:
                #log.info("column already exists: "+sql)
                return None
            else:
                raise nr

    def createTables(self):
        self.runQueryNoError(
            "create table node (id integer not null, name varbinary(255), type varbinary(32) not null, readaccess text, writeaccess text, dataaccess text, orderpos int default '1', dirty bool, primary key (id), localread text)")
        self.runQueryNoError(
            "create table nodefile (nid integer not null, filename text not null , type varbinary(16) not null, mimetype varbinary(20))")
        self.runQueryNoError("create table nodeattribute (nid integer not null, name varbinary(50) not null, value text ) ")
        self.runQueryNoError("create table nodemapping (nid integer not null, cid integer not null)")
        self.runQueryNoError("create table access (name varchar(64) not null, description text , rule text , primary key (name))")

        self.runQueryNoError("alter table node add index(type);")
        self.runQueryNoError("alter table node add index(name);")
        self.runQueryNoError("alter table node add index(orderpos);")
        self.runQueryNoError("alter table nodefile add index(nid);")
        #self.runQueryNoError("alter table nodefile add index(nid,filename);")
        self.runQueryNoError("alter table nodeattribute add index(nid);")
        self.runQueryNoError("alter table nodeattribute add index(nid,name);")
        self.runQueryNoError("alter table nodeattribute add index(name);")
        self.runQueryNoError("alter table nodemapping add index(nid);")
        self.runQueryNoError("alter table nodemapping add index(cid);")
        self.runQueryNoError("alter table nodemapping add index(nid,cid);")
        self.runQueryNoError("alter table nodemapping add index(cid,nid);")
        log.info("tables created")

    def dropTables(self):
        self.runQueryNoError("drop table access")
        self.runQueryNoError("drop table datatype")
        self.runQueryNoError("drop table user")
        self.runQueryNoError("drop table node")
        self.runQueryNoError("drop table nodefile")
        self.runQueryNoError("drop table nodeattribute")
        self.runQueryNoError("drop table nodemapping")
        log.info("tables deleted")

    def getRule(self, name):
        rule = self.runQuery("select name, description, rule from access where name=" + self.esc(name))
        if len(rule) == 1:
            return rule[0][2], rule[0][1]
        elif len(rule) > 1:
            raise DatabaseException("duplicate rule")
        else:
            raise DatabaseException("rule not found")

    def getRuleList(self):
        return self.runQuery("select name, description, rule from access order by name")

    def updateRule(self, newrule, oldname):
        try:
            self.runQuery("update access set name=" + self.esc(newrule.getName()) + ", rule=" + self.esc(newrule.getRuleStr()) +
                          ", description=" + self.esc(newrule.getDescription()) + " where name=" + self.esc(oldname))
            return True
        except:
            return False

    def addRule(self, rule):
        try:
            self.runQuery("insert into access set name=" + self.esc(rule.getName()) + ", rule=" +
                          self.esc(rule.getRuleStr()) + ", description=" + self.esc(rule.getDescription()))
            return True
        except:
            return False

    def deleteRule(self, name):
        try:
            self.runQuery("delete from access where name=" + self.esc(name))
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

    def resetNodeRule(self, rulename, newrule=""):
        for field in ["readaccess", "writeaccess", "dataaccess"]:
            self.runQuery('update node set ' + field + '="' + newrule + '" where ' + field + '="' + rulename + '"')

    def createNode(self, name, type):
        if type == "root":  # do not create a second root node
            return 0
        id = self.mkID()
        orderpos = self.mkOrderPos()
        self.runQuery(
            "insert into node (id, name, type, orderpos) values(" + id + ", " + self.esc(name) + ", '" + type + "'," + str(orderpos) + ")")
        return str(id)

    def addChild(self, nodeid, childid, check=1):
        if check:
            if childid == nodeid:
                raise ValueError("Tried to add node " + nodeid + " to itself as child")
            # does this child already exist?
            t = self.runQuery("select count(*) as num from nodemapping where nid=" + nodeid + " and cid=" + childid + "")
            if t[0][0] > 0:
                return
        self.setNodeOrderPos(childid, self.mkOrderPos())
        self.runQuery("insert into nodemapping (nid, cid) values(" + nodeid + ", " + childid + ")")

    def setAttribute(self, nodeid, attname, attvalue, check=1):
        if attvalue is None:
            raise TypeError("Attribute value is None")
        if check:
            t = self.runQuery("select count(*) as num from nodeattribute where nid=" + nodeid + " and name=" + self.esc(attname))
            if len(t) > 0 and t[0][0] > 0:
                self.runQuery("update nodeattribute set value=" + self.esc(attvalue) +
                              " where nid=" + nodeid + " and name=" + self.esc(attname))
                return
        self.runQuery(
            "insert into nodeattribute (nid, name, value) values(" + nodeid + ", " + self.esc(attname) + ", " + self.esc(attvalue) + ")")

    def set_attribute_complex(self, nodeid, attname, attvalue, check=1):
        if attvalue is None:
            raise TypeError("Attribute value is None")
        value_complex = "\x11PACK\x12" + msgpack.dumps(attvalue)
        if check:
            t = self.runQuery("select count(*) as num from nodeattribute where nid=%s and name=%s", nodeid, attname)
            if len(t) > 0 and t[0][0] > 0:
                self.runQuery("update nodeattribute set value=%s where nid=%s and name=%s", value_complex, nodeid, attname)
                return
        self.runQuery("insert into nodeattribute (nid, name, value) values(%s, %s, %s)", nodeid, attname, value_complex)

    def addFile(self, nodeid, path, type, mimetype):
        self.runQuery("insert into nodefile (nid, filename, type, mimetype) values(" +
                      nodeid + ", " + self.esc(path) + ", '" + type + "', '" + mimetype + "')")

    def removeSingleFile(self, nodeid, path):
        self.runQuery("delete from nodefile where nid = " + nodeid + " and filename=" + self.esc(path) + " limit 1")

    def getStatus(self):
        ret = []
        key = [
            "mysql_name",
            "mysql_engine",
            "mysql_version",
            "mysql_row_format",
            "mysql_rows",
            "mysql_avg_row_length",
            "mysql_data_length",
            "mysql_max_data_length",
            "mysql_index_length",
            "mysql_data_free",
            "mysql_auto_increment",
            "mysql_create_time",
            "mysql_update_time",
            "mysql_check_time",
            "mysql_collation",
            "mysql_checksum",
            "mysql_create_options",
            "mysql_comment"]
        for table in self.runQueryNoError("SHOW TABLE STATUS"):
            i = 0
            t = []
            for item in table:
                t.append((key[i], item))
                i += 1
            ret.append(t)
        return ret

    def getDBSize(self):
        l = 0
        for table in self.runQuery("SHOW TABLE STATUS"):
            if table[6]:
                l += int(table[6])
            if table[8]:
                l += int(table[8])

        return int(l)

    def _sort_nodes_by_fields_ignore_missing(self, nids, fields):
        """Sorts nodes by field (attribute) values.
        :param nids: node ids
        :param fields: field names to sort for. Prepend - to sort descending

        Returns only nodes given by `nids`, but ignores nodes which don't have an attribute with name == `fields[0]`.
        This one is slow (and may fail) for large nid counts, but faster than _sort_nodes_by_fields_get_all() for small counts.
        """
        q = "SELECT nid from {} " \
            "WHERE nid IN ({}) AND {} " \
            "ORDER BY {};"

        join_parts = []
        where_name_parts = []
        order_parts = []

        for i, f in enumerate(fields):
            alias = "a" + str(i)
            if i > 0:
                join_parts.append("nodeattribute AS " + alias)
            fname, direction = self._sql_sort_field_name_and_dir(f)
            where_name_parts.append("{}.name={}".format(alias, fname))
            order_parts.append("CAST(BINARY({}.value) as CHAR CHARACTER SET utf8) COLLATE utf8_general_ci{}".format(alias, direction))

        # looks like nodeattribute as a0 INNER JOIN nodeattribute as a1 USING (nid) INNER JOIN ...
        if len(fields) > 1:
            join_clause = "nodeattribute as a0 INNER JOIN " + "INNER JOIN".join(j + " USING (nid)" for j in join_parts)
        else:
            join_clause = "nodeattribute as a0"
        where_name_clause = " AND ".join(where_name_parts)
        order_clause = ", ".join(order_parts)
        query = q.format(join_clause, nids, where_name_clause, order_clause)
        return [str(r[0]) for r in self.runQuery(query)]

    def _sort_nodes_by_fields_get_all(self, nids, fields):
        """This one ignores nids and returns all nodes which have a field with name == fields[0].
        Works for every nid count but is slower than _sort_nodes_by_fields_ignore_missing() for small counts.
        """

        q = "SELECT nid from {} " \
            "WHERE {} " \
            "ORDER BY {};"

        join_parts = []
        where_name_parts = []
        order_parts = []

        for i, f in enumerate(fields):
            alias = "a" + str(i)
            if i > 0:
                join_parts.append("nodeattribute AS " + alias)
            fname, direction = self._sql_sort_field_name_and_dir(f)
            where_name_parts.append("{}.name={}".format(alias, fname))
            order_parts.append("CAST(BINARY({}.value) as CHAR CHARACTER SET utf8) COLLATE utf8_general_ci{}".format(alias, direction))

        # looks like nodeattribute as a0 INNER JOIN nodeattribute as a1 USING (nid) INNER JOIN ...
        if len(fields) > 1:
            join_clause = "nodeattribute as a0 INNER JOIN " + "INNER JOIN".join(j + " USING (nid)" for j in join_parts)
        else:
            join_clause = "nodeattribute as a0"
        where_name_clause = " AND ".join(where_name_parts)
        order_clause = ", ".join(order_parts)
        query = q.format(join_clause, where_name_clause, order_clause)
        return [str(r[0]) for r in self.runQuery(query)]

    def _sort_nodes_by_fields_full(self, nids, fields):
        """This one is very slow, but sorts by each field even when some sort fields are missing.
        Only returns matching nids.
        """
        q = "SELECT nid from (SELECT id AS nid FROM node WHERE id IN ({})) as n LEFT JOIN {} " \
            "ORDER BY {};"

        join_parts = []
        order_parts = []

        for i, f in enumerate(fields):
            alias = "a" + str(i)
            fname, direction = self._sql_sort_field_name_and_dir(f)
            join_parts.append("(SELECT nid, value from nodeattribute WHERE name={} AND nid IN ({})) AS {}".format(fname, nids, alias))
            order_parts.append("CAST(BINARY({}.value) as CHAR CHARACTER SET utf8) COLLATE utf8_general_ci{}".format(alias, direction))

        join_clause = " LEFT JOIN ".join(j + " USING (nid)" for j in join_parts)
        order_clause = ", ".join(order_parts)
        query = q.format(nids, join_clause, order_clause)
        return [str(r[0]) for r in self.runQuery(query)]

    def sort_nodes_by_fields(self, nids, fields):
        """Sorts nodes by field (attribute) values.
        :param nids: node ids
        :param fields: field names to sort for. Prepend - to sort descending
        """
        return self._sort_nodes_by_fields_get_all(nids, fields)

    def _get_nodes_by_field_value(self, **kwargs):
        sql_parameters = ()
        sql_conditions = []
        sql_query = """
SELECT DISTINCT n.id
FROM `node` n INNER JOIN
     `nodeattribute` a ON a.`nid` = n.`id`
        """

        if "parent_id" in kwargs:
            parent_id = kwargs["parent_id"]
            sql_conditions.append("(n.`id` IN (SELECT `cid` FROM `nodemapping` nm WHERE nm.`nid` = %s))")
            sql_parameters += (parent_id, )
            del kwargs["parent_id"]

        for field, value in kwargs.items():
            if value == '__is_set__':
                sql_conditions.append("(a.`name` = %s AND a.`value` IS NOT NULL AND a.`value` != %s)")
                sql_parameters += (field, '', )
            else:
                sql_conditions.append("(a.`name` = %s AND a.`value` = %s)")
                sql_parameters += (field, value, )

        if sql_conditions:
            sql_query += " WHERE " + " AND ".join(sql_conditions)

        return [str(r[0]) for r in self.runQuery(sql_query, *sql_parameters)]

    def _get_child_nodes_by_field_value(self, nid, **kwargs):
        sql_parameters = ()
        sql_conditions = []
        sql_query = """
SELECT DISTINCT nt.nid
FROM (
    SELECT `nid01` AS `nid` FROM `nodetree` nt01 WHERE `nid01` = %s
    UNION ALL
    SELECT `nid02` AS `nid` FROM `nodetree` nt02 WHERE `nid01` = %s
    UNION ALL
    SELECT `nid03` AS `nid` FROM `nodetree` nt03 WHERE `nid01` = %s
    UNION ALL
    SELECT `nid04` AS `nid` FROM `nodetree` nt04 WHERE `nid01` = %s
    UNION ALL
    SELECT `nid05` AS `nid` FROM `nodetree` nt05 WHERE `nid01` = %s
    UNION ALL
    SELECT `nid06` AS `nid` FROM `nodetree` nt06 WHERE `nid01` = %s
    UNION ALL
    SELECT `nid07` AS `nid` FROM `nodetree` nt07 WHERE `nid01` = %s
    UNION ALL
    SELECT `nid08` AS `nid` FROM `nodetree` nt08 WHERE `nid01` = %s
    UNION ALL
    SELECT `nid09` AS `nid` FROM `nodetree` nt09 WHERE `nid01` = %s
    UNION ALL
    SELECT `nid10` AS `nid` FROM `nodetree` nt10 WHERE `nid01` = %s
) AS `nt` INNER JOIN
     `nodeattribute` a ON a.`nid` = nt.`nid`
        """
        sql_parameters += (nid, ) * 10

        for field, value in kwargs.items():
            if value == '__is_set__':
                sql_conditions.append("(a.`name` = %s AND a.`value` IS NOT NULL AND a.`value` != %s)")
                sql_parameters += (field, '', )
            else:
                sql_conditions.append("(a.`name` = %s AND a.`value` = %s)")
                sql_parameters += (field, value, )

        if sql_conditions:
            sql_query += " WHERE " + " AND ".join(sql_conditions)

        return [str(r[0]) for r in self.runQuery(sql_query, *sql_parameters)]

    def get_nodes_by_field_value(self, **kwargs):
        return self._get_nodes_by_field_value(**kwargs)

    def get_child_nodes_by_field_value(self, nid, **kwargs):
        return self._get_child_nodes_by_field_value(nid, **kwargs)
