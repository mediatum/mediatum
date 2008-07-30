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
import traceback
import thread
from connector import Connector

try:
    import sqlite3 as sqlite
    import sqlite3.OperationalError as OperationalError
except:
    from pysqlite2 import dbapi2 as sqlite
    from pysqlite2.dbapi2 import OperationalError as OperationalError

#from time import *
from core.db.database import initDatabaseValues

if __name__ == "__main__":
    sys.path += [".."]

import core.config as config
from utils import *

debug = 0
log = logging.getLogger('database')

sqlite_lock = thread.allocate_lock()

class SQLiteConnector(Connector):

    def __init__(self,db=None):
        config.initialize()
        if db==None:
            if not os.path.exists(config.settings["paths.datadir"]+"db/imagearch.db"):   
                try:
                    os.makedirs(os.path.dirname(config.settings["paths.datadir"]+"db/"))
                except OSError:
                    pass
            db = config.settings["paths.datadir"]+"db/imagearch.db"
            self.isInitialized()
        else:
            self.db = db

    def isInitialized(self):
        try:
            self.execute("select id from node where type='root'")
            return True
        except sqlite.OperationalError:
            self.createTables()
            initDatabaseValues(self)
            self.commit()
        return False

    def esc(self, text):
        return "'"+text.replace("'","\\'")+"'"
    
    def close(self):
        pass

    def execute(self,sql, obj=None):
        global sqlite_lock
        sqlite_lock.acquire()
        try:
            fi = open("/tmp/sqlite.log", "ab+")
            fi.write(sql+"\n")
            fi.close()

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
        finally:
            sqlite_lock.release()

    def runQuery(self, sql, obj=None):
        if debug:
            log.debug(sql)
        return self.execute(sql,obj)

    def runQueryNoError(self, sql, obj=None):
        global debug
        try:
            return self.execute(sql, obj)
        except:
            log.debug(sql)

    def createTables(self):
        self.runQueryNoError("CREATE TABLE [nodeaccess] ([name] VARCHAR(64)  NOT NULL PRIMARY KEY, [description] TEXT  NULL,[rule] TEXT  NULL)")
        self.runQueryNoError("CREATE TABLE [node] ([id] INTEGER  NOT NULL PRIMARY KEY AUTOINCREMENT, [name] VARCHAR(255)  NULL, [type] VARCHAR(32)  NULL, [readaccess] TEXT  NULL, [writeaccess] TEXT  NULL, [dataaccess] TEXT  NULL, [lastchange] DATE DEFAULT CURRENT_DATE NULL, [orderpos] INTEGER DEFAULT '1' NULL)")
        self.runQueryNoError("CREATE TABLE [nodeattribute] ([nid] INTEGER DEFAULT '0' NOT NULL, [name] VARCHAR(50)  NOT NULL, [value] TEXT  NULL)")
        self.runQueryNoError("CREATE TABLE [nodefile] ([nid] INTEGER DEFAULT '0' NOT NULL, [filename] TEXT  NOT NULL, [type] VARCHAR(32)  NOT NULL, [mimetype] VARCHAR(32)  NULL)")
        self.runQueryNoError("CREATE TABLE [nodemapping] ([nid] INTEGER DEFAULT '0' NOT NULL, [cid] INTEGER DEFAULT '0' NOT NULL)")
        
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
        self.commit()

    def dropTables(self):
        self.runQueryNoError("drop table nodeaccess")
        self.runQueryNoError("drop table user")
        self.runQueryNoError("drop table node")
        self.runQueryNoError("drop table nodefile")
        self.runQueryNoError("drop table nodeattribute")
        self.runQueryNoError("drop table nodemapping")
        self.commit()
        log.info("tables deleted")

    def clearTables(self):
        self.runQueryNoError("delete from access")
        self.runQueryNoError("delete from user")
        self.runQueryNoError("delete from node")
        self.runQueryNoError("delete from nodefile")
        self.runQueryNoError("delete from nodeattribute")
        self.runQueryNoError("delete from nodemapping")
        self.commit()
        log.info("tables cleared")
        
    def getMappings(self, direction):
        if direction>0:
            return self.runQuery("select nid,cid from nodemapping order by nid,cid")
        else:
            return self.runQuery("select cid,nid from nodemapping order by cid,nid")
    
    def getRule(self, name):
        rule = self.runQuery("select name, description, rule from nodeaccess where name=" + self.esc(name))
        if len(rule)==1:
            return rule[0][2], rule[0][1]
        elif len(rule)>1:
            raise "DuplicateRuleError"
        else:
            raise "RuleNotFoundError"
    
    def getRuleList(self):
        return self.runQuery("select name, description, rule from nodeaccess order by name")

    def updateRule(self, rule):
        #try:
        sql = "update nodeaccess set rule='"+rule.getRuleStr()+"', description='"+rule.getDescription()+"' where name='" + rule.getName()+"'"
        self.runQuery(sql)
        return True
        #except:
        #    return False
    
    def addRule(self, rule):
        try:
            self.runQuery("insert into nodeaccess (name, rule, description) values('"+rule.getName()+"', '"+rule.getRuleStr()+"', '"+rule.getDescription()+"')")
            return True
        except:
            return False

    def deleteRule(self, name):
        try:
            self.runQuery("delete from nodeaccess where name='" + name+"'")
            return True
        except:
            return False

    def getAllDBRuleNames(self):
        ret = {}
        for field in ["readaccess", "writeaccess", "dataaccess"]:
            for names in self.runQuery('select distinct('+field+') from node where '+field+' not like "{%"'):
                rules = names[0].split(",")
                for rule in rules:
                    if rule!="":
                        ret[rule]=""
        return ret.keys()   
        
    def ruleUsage(self, rulename):
        result = self.runQuery('select count(*) from node where readaccess="'+rulename+'" or writeaccess="'+rulename+'" or dataaccess="'+rulename+'"')
        return int(result[0][0])
        
    def resetNodeRule(self, rulename):
        for field in ["readaccess", "writeaccess", "dataaccess"]:
            self.runQuery('update node set '+field+'="" where '+field+'="'+rulename+'"')
            
            
    """ node section """
    def getRootID(self):
        nodes = self.runQuery("select id from node where type='root'")
        if len(nodes)<=0:
            return None
        if len(nodes)>1:
            raise "More than one root node"
        return str(nodes[0][0])

    def getNode(self,id):
        t = self.runQuery("select id,name,type,readaccess,writeaccess,dataaccess,orderpos from node where id=" + id)
        if len(t) == 1:
            return str(t[0][0]),t[0][1],t[0][2],t[0][3],t[0][4],t[0][5],t[0][6] # id,name,type,read,write,data,orderpos
        elif len(t) == 0:
            log.error("No node for ID "+str(id))
            return None
        else:
            log.error("More than one node for id "+str(id))
            return None

    def getNamedNode(self, parentid, name):
        t = self.runQuery("select id from node,nodemapping where node.name="+self.esc(name)+" and node.id = nodemapping.cid and nodemapping.nid = "+parentid)
        if len(t) == 0:
            return None
        else:
            return t[0][0]

    def deleteNode(self, id):
        self.runQuery("delete from node where id=" + id)
        self.runQuery("delete from nodemapping where cid=" + id)
        self.runQuery("delete from nodeattribute where nid=" + id)
        self.runQuery("delete from nodefile where nid=" + id)

        # WARNING: this might create orphans
        self.runQuery("delete from nodemapping where nid=" + id)
        log.info("node "+id+" deleted")

    def mkOrderPos(self):
        t = self.runQuery("select max(orderpos) as orderpos from node")
        if len(t)==0 or t[0][0] is None:
            return "1"
        orderpos = t[0][0] + 1
        return orderpos

    def createNode(self, name, type):
        orderpos = self.mkOrderPos()
        self.runQuery("insert into node (name,type,orderpos) values(?,?,?)",(name,type,orderpos))
        res = self.runQuery("select max(id) from node")
        return str(res[0][0])
    
    def addChild(self, nodeid, childid, check=1):
        if check:
            if childid == nodeid:
                raise "Tried to add node "+nodeid+" to itself as child"
            # does this child already exist?
            t = self.runQuery("select count(*) as num from nodemapping where nid="+nodeid+" and cid="+childid)
            if t[0][0]>0:
                return
        self.setNodeOrderPos(childid, self.mkOrderPos())
        self.runQuery("insert into nodemapping (nid, cid) values(?,?)",(nodeid,childid))

    def setAttribute(self, nodeid, attname, attvalue, check=1):
        if attvalue is None:
            raise "Attribute value is None"
        if check:
            t = self.runQuery("select count(*) as num from nodeattribute where nid="+nodeid+" and name='"+attname+"'")
            if len(t)>0 and t[0][0]>0:
                self.runQuery("update nodeattribute set value='"+attvalue+"' where nid="+nodeid+" and name='"+attname+"'")
                return
        self.runQuery("insert into nodeattribute (nid, name, value) values(?,?,?)", (nodeid,attname,attvalue))

    def addFile(self, nodeid, path, type, mimetype):
        self.runQuery("insert into nodefile (nid, filename, type, mimetype) values(?,?,?,?)", (nodeid,path,type,mimetype))

    def getNodeIDsForSchema(self, schema, datatype="*"):
        return self.runQuery('select id from node where type like "%/'+schema+'" or type ="'+schema+'"')


    def getStatus(self):
        ret = []
        key = ["sqlite_type", "sqlite_name", "sqlite_tbl_name", "sqlite_rootpage", "sqlite_sql"]
        for table in self.runQuery("select * from sqlite_master"):
            i=0
            t = []
            for item in table:
                t.append((key[i],item))
                i += 1
                
            items = self.runQuery("select * from sqlite_stat1 where tbl='"+t[2][1]+"'")
            if len(items)>0:
                t.append(("sqplite_items_count", str(items[0][2]).split(" ")[0]))

            ret.append(t)

        return ret

        
    def getDBSize(self):
        import os
        return os.stat(config.settings["paths.datadir"]+"db/imagearch.db")[6]
