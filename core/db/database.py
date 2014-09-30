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

import core.config as config

_db = None
_dbconn = None


class DatabaseException:

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "db exception: " + self.msg + "\n"


def getConnection():
    global _db, _dbconn
    if not _db:
        type = config.get("database.type", "")
        if type == "sqlite" or type == "sqllite":
            print "Initializing sqlite database"
            from core.db import sqliteconnector
            _db = sqliteconnector.SQLiteConnector
            _dbconn = _db()
            _db = lambda: _dbconn
        else:
            print "Initializing mysql database"
            from core.db import mysqlconnector
            _db = mysqlconnector.MYSQLConnector
    return _db()


def initDatabaseValues(conn):
    conn.runQuery("insert into node (id,name,type) values(1,'Gesamtbestand', 'root')")
    conn.runQuery("insert into node (id,name,type) values(2,'users', 'users')")
    conn.runQuery("insert into node (id,name,type) values(3,'metadatatypes', 'metadatatypes')")
    conn.runQuery("insert into node (id,name,type) values(4,'workflows', 'workflows')")
    conn.runQuery("insert into node (id,name,type) values(5,'usergroups', 'users')")
    conn.runQuery("insert into node (id,name,type) values(10,'collections', 'collections')")
    conn.runQuery("insert into nodeattribute (nid,name,value) values(10,'label','Gesamtbestand')")

    conn.runQuery("insert into nodeattribute (nid,name,value) values(12,'label','Kollektionen')")
    conn.runQuery("insert into node (id,name,type) values(11,'home', 'home')")
    conn.runQuery("insert into node (id,name,type) values(12,'navigation', 'navigation')")
    conn.runQuery("insert into nodemapping (nid,cid) values(1,2)")
    conn.runQuery("insert into nodemapping (nid,cid) values(1,3)")
    conn.runQuery("insert into nodemapping (nid,cid) values(1,4)")
    conn.runQuery("insert into nodemapping (nid,cid) values(1,5)")
    conn.runQuery("insert into nodemapping (nid,cid) values(1,10)")
    conn.runQuery("insert into nodemapping (nid,cid) values(1,11)")
    conn.runQuery("insert into nodemapping (nid,cid) values(1,12)")

    adminuser = config.get("user.adminuser", "Administrator")
    admingroup = config.get("user.admingroup", "Administration")
    conn.runQuery("insert into node (id,name,type) values(6,'" + adminuser + "', 'user')")
    conn.runQuery("insert into nodemapping (nid,cid) values(2,6)")
    conn.runQuery("insert into nodeattribute (nid,name,value) values(6,'password'," +
                  "'226fa8e6cbb1f4e25019e2645225fd47')")  # xadmin1
    conn.runQuery("insert into nodeattribute (nid,name,value) values(6,'email','admin@mediatum')")
    conn.runQuery("insert into nodeattribute (nid,name,value) values(6,'opts','c')")

    conn.runQuery("insert into node (id,name,type) values(7,'" + config.get("user.guestuser", "Gast") + "', 'user')")
    conn.runQuery("insert into nodeattribute (nid,name,value) values(7,'email','guest@mediatum')")
    conn.runQuery("insert into nodemapping (nid,cid) values(2,7)")
    conn.runQuery("insert into nodemapping (nid,cid) values(13,7)")
    conn.runQuery("insert into node (id,name,type) values(8,'" + admingroup + "', 'usergroup')")
    conn.runQuery("insert into nodeattribute (nid,name,value) values(8,'opts','ew')")
    conn.runQuery("insert into nodemapping (nid,cid) values(5,8)")
    conn.runQuery("insert into nodemapping (nid,cid) values(8,6)")

    conn.runQuery("insert into node (id,name,type) values(13,'Gast', 'usergroup')")
    conn.runQuery("insert into nodemapping (nid,cid) values(5,13)")
