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
import traceback
import thread
from connector import Connector

from core.db.database import initDatabaseValues

if __name__ == "__main__":
    sys.path += [".."]

import core.config as config
from utils.utils import *

debug = 0

log = logging.getLogger('database')

class MYSQLConnector(Connector):

    def __init__(self):
        config.initialize()
        self.database = config.settings["database.db"]
        self.user = config.settings["database.user"]
        self.passwd = config.settings["database.passwd"]

        self.db=MySQLdb.connect(user = self.user, passwd = self.passwd, db = self.database)
        self.dblock=thread.allocate_lock()
        self.nodes = {}

        function = str(traceback.extract_stack()[-2][0])+":"+str(traceback.extract_stack()[-2][2])
        log.info("Connecting to ["+self.user+"@"+self.database+"] "+function)

        try:
            r = self.runQuery("select id from node where type='root'")
            r[0]
        except MySQLdb.ProgrammingError:
            self.createTables()
            initDatabaseValues(self)
        except IndexError:
            initDatabaseValues(self)


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
                #self.db.ping()
                ok = 1
        except MySQLdb.OperationalError, nr:
            ok = 0
            log.warning("Pinging failed ("+str(nr)+")... reconnecting to ["+self.user+"@"+self.database+"]")
            self.db = None

        if not ok:
            self.db=MySQLdb.connect(user = self.user, passwd = self.passwd, db = self.database)
        return self.db

    def esc(self,s):
        try:
            return self.db.escape(s)
        except:
            try:
                return MySQLdb.escape(s,self.db.converter)
            except:
                #TODO: this should not be necessary.
                #maybe switch to
                #       cursor.execute("select whatever from whomever where something = %s", my_parameter)
                #?
                s = str(s)
                return "'" + s.replace('\\','\\\\').replace('"','\\"').replace('\'','\\\'') + "'"

    def execute(self,sql):
        self.dblock.acquire()
        try:
            while 1:
                try:
                    self._reconnect()
                    c = self.db.cursor()
                    c.execute(sql)
                    result = c.fetchall()
                    c.close()
                    self.db.commit()
                    return result
                except MySQLdb.OperationalError, nr:
                    if nr[0] == 2002:
                        log.error("can't connect to sql server while executing \""+sql+"\"")
                        self.db = None
                        sleep(5)
                        continue
                    if nr[0] == 2006:
                        log.error("mysql server has gone away while executing \""+sql+"\"")
                        self.db = None
                        sleep(5)
                        continue
                    elif nr[0] == 2013:
                        log.error("lost connection to database while executing \""+sql+"\"")
                        self.db = None
                        sleep(5)
                        continue
                    else:
                        raise
        finally:
            self.dblock.release()


    def runQuery(self, sql):
        global debug
        self.dblock.acquire()
        try:
            if debug:
                log.debug(sql)
                c = self.db.cursor()
                c.execute("explain "+sql)
                result = c.fetchall()
                c.close()
                type = result[0][1]
                extra = result[0][7]
                if type == 'ALL' or "temporary" in extra.lower() or "filesort" in extra.lower():
                    print "========================================================================"
                    print "Warning: Slow SQL Statement (type="+type+", extra="+extra+")"
                    print sql
                    print "========================================================================"

        finally:
            self.dblock.release()

        result = self.execute(sql)
        return result


    def runQueryNoError(self, sql):
        print sql
        global debug
        if debug:
            log.debug(sql)
        try:
            return self.execute(sql)
        except MySQLdb.OperationalError, nr:
            if nr[0] == 1050:
                log.info("table already exists: "+sql)
                return None
            elif nr[0] == 1051:
                log.info("table doesn't exists: "+sql)
                return None
            else:
                raise nr


    def createTables(self):
        self.runQueryNoError("create table node (id integer not null, name varbinary(255), type varbinary(32) not null, readaccess text, writeaccess text, dataaccess text, orderpos int default '1', primary key (id))")
        self.runQueryNoError("create table nodefile (nid integer not null, filename text not null , type varbinary(16) not null, mimetype varbinary(20))")
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


    def getMappings(self, direction):
        if direction > 0:
            return self.runQuery("select nid,cid from nodemapping order by nid,cid")
        else:
            return self.runQuery("select cid,nid from nodemapping order by cid,nid")


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
        if len(rule)==1:
            return rule[0][2], rule[0][1]
        elif len(rule)>1:
            raise "DuplicateRuleError"
        else:
            raise "RuleNotFoundError"
    

    def getRuleList(self):
        return self.runQuery("select name, description, rule from access order by name")

    def updateRule(self, rule):
        try:
            self.runQuery("update access set rule=" + self.esc(rule.getRuleStr()) + ", description=" + self.esc(rule.getDescription()) + " where name=" + self.esc(rule.getName()))
            return True
        except:
            return False

    def addRule(self, rule):
        try:
            self.runQuery("insert into access set name=" + self.esc(rule.getName()) + ", rule=" + self.esc(rule.getRuleStr()) + ", description=" + self.esc(rule.getDescription()))
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
            for names in self.runQuery('select distinct('+field+') from node where '+field+' not like "{%"'):
                rules = names[0].split(",")
                for rule in rules:
                    if rule!="":
                        ret[rule]=""
        return ret.keys()
        
    def ruleUsage(self, rulename):
        result = self.runQuery('select count(*) from node where readaccess="'+rulename+'" or writeaccess="'+rulename+'" or dataaccess="'+rulename+'"')
        return int(result[0][0])

    def resetNodeRule(self, rulename, newrule=""):
        for field in ["readaccess", "writeaccess", "dataaccess"]:
            self.runQuery('update node set '+field+'="'+newrule+'" where '+field+'="'+rulename+'"')

    
    #
    # node section
    #   
    def getRootID(self):
        nodes = self.runQuery("select id from node where type='root'")
        if len(nodes)<=0:
            return None
        if len(nodes)>1:
            raise "More than one root node"
        return str(nodes[0][0])
        

    def getNode(self, id):
        t = self.runQuery("select id,name,type,readaccess,writeaccess,dataaccess,orderpos from node where id=" + str(id))
        if len(t) == 1:
            return str(t[0][0]),t[0][1],t[0][2],t[0][3],t[0][4],t[0][5],t[0][6] # id,name,type,read,write,data,orderpos
        elif len(t) == 0:
            log.error("No node for ID "+str(id))
            return None
        else:
            log.error("More than one node for id "+str(id))
            return None
            
    def getNodeIdByAttribute(self, attributename, attributevalue):
        if attributename.endswith("access"):
            t = self.runQuery("select id from node where "+attributename+" like '%" + str(attributevalue)+"%'")
        else:
            if attributevalue=="*":
                t = self.runQuery("select node.id from node, nodeattribute where node.id=nodeattribute.nid and nodeattribute.name='" + str(attributename)+"'")
            else:
                t = self.runQuery("select node.id from node, nodeattribute where node.id=nodeattribute.nid and nodeattribute.name='" + str(attributename)+"' and nodeattribute.value='"+str(attributevalue)+"'")
        if len(t)==0:
            return []
        else:
            ret = []
            for i in t:
                if i[0] not in ret:
                    ret.append(i[0])
            return ret
            
                
    def getNamedNode(self, parentid, name):
        t = self.runQuery("select id from node,nodemapping where node.name="+self.esc(name)+" and node.id = nodemapping.cid and nodemapping.nid = "+parentid)
        if len(t) == 0:
            t = self.runQuery("select id from node,nodemapping where node.type="+self.esc(name)+" and node.id = nodemapping.cid and nodemapping.nid = "+parentid)
            if len(t)==1:
                return t[0][0]
            else:
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


    def mkID(self):
        # TODO: use mysql autoincrementer
        t = self.runQuery("select max(id) as maxid from node")
        if len(t)==0 or t[0][0] is None:
            return "1"
        id = t[0][0] + 1
        return str(id)

    def mkOrderPos(self):
        # TODO: use mysql autoincrementer
        t = self.runQuery("select max(orderpos) as orderpos from node")
        if len(t)==0 or t[0][0] is None:
            return "1"
        orderpos = t[0][0] + 1
        return orderpos

    def createNode(self, name, type):
        id = self.mkID()
        orderpos = self.mkOrderPos()
        self.runQuery("insert into node (id, name, type, orderpos) values(" + id + ", " + self.esc(name) + ", '" + type + "',"+str(orderpos)+")")
        
        #self.setAttribute(self, id, "creationdate", str(time()))
        ##### time.strftime(format, time.localtime(str))
        
        #self.setAttribute(self, id, "creator", self.requestuser)
            
        #log.info("node "+id+" ("+name+") created")
        return str(id)
    
    def addChild(self, nodeid, childid, check=1):
        if check:
            if childid == nodeid:
                raise "Tried to add node "+nodeid+" to itself as child"
            # does this child already exist?
            t = self.runQuery("select count(*) as num from nodemapping where nid=" + nodeid + " and cid=" + childid + "")
            if t[0][0]>0:
                return
        self.setNodeOrderPos(childid, self.mkOrderPos())
        self.runQuery("insert into nodemapping (nid, cid) values(" + nodeid + ", " + childid + ")")

    def setAttribute(self, nodeid, attname, attvalue, check=1):
        if attvalue is None:
            raise "Attribute value is None"
        if check:
            t = self.runQuery("select count(*) as num from nodeattribute where nid=" + nodeid + " and name=" + self.esc(attname))
            if len(t)>0 and t[0][0]>0:
                self.runQuery("update nodeattribute set value=" + self.esc(attvalue) + " where nid=" + nodeid + " and name=" + self.esc(attname))
                return
        self.runQuery("insert into nodeattribute (nid, name, value) values(" + nodeid + ", " + self.esc(attname) + ", " + self.esc(attvalue) + ")")

    def addFile(self, nodeid, path, type, mimetype):
        self.runQuery("insert into nodefile (nid, filename, type, mimetype) values(" + nodeid + \
                    ", " + self.esc(path) + ", '" + type + "', '" + mimetype+ "')")

    def getNodeIDsForSchema(self, schema, datatype="*"):
        return self.runQuery('select id from node where type like "%/'+schema+'" or type ="'+schema+'"')
        
    def getStatus(self):
        ret = []
        key = ["mysql_name", "mysql_engine", "mysql_version", "mysql_row_format", "mysql_rows", "mysql_avg_row_length", "mysql_data_length", "mysql_max_data_length", "mysql_index_length", "mysql_data_free", "mysql_auto_increment",
            "mysql_create_time", "mysql_update_time", "mysql_check_time", "mysql_collation", "mysql_checksum", "mysql_create_options", "mysql_comment"]
        for table in self.runQueryNoError("SHOW TABLE STATUS"):
            i=0
            t = []
            for item in table:
                t.append((key[i],item))
                i += 1
            ret.append(t)
        return ret
        
        
    def getDBSize(self):
        l = 0
        for table in self.runQueryNoError("SHOW TABLE STATUS"):
            l+= int(table[6])
            l+= int(table[8])
            
        return int(l)
        
        
        
