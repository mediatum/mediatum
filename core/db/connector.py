#!/usr/bin/python
"""
 mediatum - a multimedia content repository

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

from core.db.database import initDatabaseValues
import core.config as config
from utils import *

debug = 0
log = logging.getLogger('database')

class Connector:
    def esc(self, text):
        return "'"+text.replace("'","\\'")+"'"
    
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
        return self.runQuery("select value from nodeattribute where name=" + self.esc(name))
    
    def getSortOrder(self, field):
        return self.runQuery("select nid,value from nodeattribute where name="+self.esc(field))

    def getActiveACLs(self):
        mylist = self.runQuery("select distinct readaccess from node where readaccess not like '{user %}'")
        acls = []
        for acl in mylist:
            acls += acl.split(',')
        return acls

    def getFiles(self, nodeid):
        return self.runQuery("select filename,type,mimetype from nodefile where nid="+nodeid)
    def removeFile(self, nodeid, path):
        self.runQuery("delete from nodefile where nid = "+nodeid+" and filename="+self.esc(path))
    def removeAttribute(self, nodeid, attname):
        self.runQuery("delete from nodeattribute where nid=" + nodeid + " and name=" + self.esc(attname))
    
    def setNodeName(self, id, name):
        self.runQuery("update node set name = "+self.esc(name)+" where id = "+id)

    def setNodeOrderPos(self, id, orderpos):
        self.runQuery("update node set orderpos = "+str(orderpos)+" where id = "+id)

    def setNodeReadAccess(self, id, access):
        self.runQuery("update node set readaccess = "+self.esc(access)+" where id = "+id)

    def setNodeWriteAccess(self, id, access):
        self.runQuery("update node set writeaccess = "+self.esc(access)+" where id = "+id)

    def setNodeDataAccess(self, id, access):
        self.runQuery("update node set dataaccess = "+self.esc(access)+" where id = "+id)

    def setNodeType(self, id, type):
        self.runQuery("update node set type = "+self.esc(type)+" where id = "+id)

