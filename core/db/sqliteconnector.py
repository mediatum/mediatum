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

import sqlite3 as sqlite
try:
    import sqlite3 as sqlite
except:
    from pysqlite2 import dbapi2 as sqlite

#from time import *
from core.db.database import initDatabaseValues

if __name__ == "__main__":
    sys.path += [".."]

import core.config as config
from utils import *

debug = 0
log = logging.getLogger('database')


class SQLiteConnector:

    def __init__(self,db=None):
        config.initialize()
        if db==None:
            if not os.path.exists(config.settings["paths.datadir"]+"db/imagearch.db"):   
                try:
                    os.makedirs(os.path.dirname(config.settings["paths.datadir"]+"db/"))
                except OSError:
                    pass
            self.con = sqlite.connect(config.settings["paths.datadir"]+"db/imagearch.db", check_same_thread=False)
        else:
            self.con = sqlite.connect(db, check_same_thread=False)
        self.cur = self.con.cursor()
        self.con.text_factory = type("")
        self.isInitialized()

    def isInitialized(self):
        try:
            self.cur.execute("select id from node where type='root'")
            return True
        except sqlite.OperationalError:
            self.createTables()
            initDatabaseValues(self)
            self.commit()
        return False

    def esc(self, text):
        return "'"+text.replace("'","\\'")+"'"
    
    def close(self):
        try:
            self.cur.close()
        finally:
            self.con.close()

    def execute(self,sql, obj=None):
        if obj:
            res = self.cur.execute(sql, obj)
        else:
            res = self.cur.execute(sql)
        self.commit()
        s = res.fetchall()
        return s

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

    def commit(self):
    	self.con.commit()

    def rollback(self):
        self.con.rollback()

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


    """ ACL rule section """
    def getRule(self, name):
        rule = self.runQuery("select name, description, rule from nodeaccess where name='" + name + "'")
        if len(rule)==1:
            return rule[0][2], rule[0][1]
        elif len(rule)>1:
            raise "Duplicate rule "+str(name)
        else:
            raise "no such rule "+str(name)
    
    def getRuleList(self):
        return self.runQuery("select name, description, rule from nodeaccess order by name")

    def updateRule(self, rule):
        #try:
        sql = "update nodeaccess set rule='"+rule.getRuleStr()+"', description='"+rule.getDescription()+"' where name='" + rule.getName()+"'"
        print sql
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

    def setNodeName(self, id, name):
        self.runQuery("update node set name ='"+name+"' where id="+id)

    def setNodeOrderPos(self, id, orderpos):
        self.runQuery("update node set orderpos="+str(orderpos)+" where id="+id)

    def setNodeReadAccess(self, id, access):
        self.runQuery("update node set readaccess='"+access+"' where id="+id)

    def setNodeWriteAccess(self, id, access):
        self.runQuery("update node set writeaccess='"+access+"' where id="+id)

    def setNodeDataAccess(self, id, access):
        self.runQuery("update node set dataaccess='"+access+"' where id="+id)

    def setNodeType(self, id, type):
        self.runQuery("update node set type='"+type+"' where id="+id)

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

    def removeChild(self, nodeid, childid):
        self.runQuery("delete from nodemapping where nid=" + nodeid + " and cid=" + childid)

    def getChildren(self, nodeid):
        t = self.runQuery("select cid from nodemapping where nid="+nodeid+" order by cid")
        idlist = []
        for id in t:
            idlist += [str(id[0])]
        return idlist

    def getParents(self, nodeid):
        t = self.runQuery("select nid from nodemapping where cid="+nodeid)
        idlist = []
        for id in t:
            idlist += [str(id[0])]
        return idlist

    def getAttributes(self, nodeid):
        t = self.runQuery("select name,value from nodeattribute where nid=" + nodeid)
        attributes = {}
        for name,value in t:
            if value:
                attributes[name] = value
        return attributes

    def getMetaFields(self, name):
        return self.runQuery("select value from nodeattribute where name='"+name+"'")
    
    def getSortOrder(self, field):
        return self.runQuery("select nid,value from nodeattribute where name="+self.esc(field))

    def setAttribute(self, nodeid, attname, attvalue, check=1):
        if attvalue is None:
            raise "Attribute value is None"
        if check:
            t = self.runQuery("select count(*) as num from nodeattribute where nid="+nodeid+" and name='"+attname+"'")
            if len(t)>0 and t[0][0]>0:
                self.runQuery("update nodeattribute set value='"+attvalue+"' where nid="+nodeid+" and name='"+attname+"'")
                return
        self.runQuery("insert into nodeattribute (nid, name, value) values(?,?,?)", (nodeid,attname,attvalue))

    def removeAttribute(self, nodeid, attname):
        self.runQuery("delete from nodeattribute where nid="+nodeid+" and name='"+attname+"'")

    def getFiles(self, nodeid):
        return self.runQuery("select filename,type,mimetype from nodefile where nid="+nodeid)

    def addFile(self, nodeid, path, type, mimetype):
        self.runQuery("insert into nodefile (nid, filename, type, mimetype) values(?,?,?,?)", (nodeid,path,type,mimetype))

    def removeFile(self, nodeid, path):
        self.runQuery("delete from nodefile where nid="+nodeid+" and filename='"+path+"'")
