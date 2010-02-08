"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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

# create all needed views for content and container types (mediatum version > 0.5.1

import sys
sys.path+=["."]

import core
import core.tree as tree
import core.config as config

from core.tree import db
from core.datatypes import loadAllDatatypes

container = []
content = []
dbname = config.get("database.db")
viewnames = ["containermapping", "contentmapping"]


def createView(dbname, viewname, viewsql):
    if str(dbname) not in ["", "None"]:
        sql = 'CREATE OR REPLACE VIEW `%s`.`%s` AS %s' %(dbname, viewname, viewsql)
    else:
        sql = 'CREATE VIEW `%s` AS %s' %(viewname, viewsql)
    db.runQuery(sql)
    print "view '%s' created"  % viewname

    
for dtype in loadAllDatatypes():
    if dtype.getName() not in ["root", "navitem", "home"]:
        n = tree.Node("", type=dtype.name)
        
        if hasattr(n, "isSystemType") and n.isSystemType()==0:
            if hasattr(n, "isContainer") and n.isContainer()==1 :
                container.append(dtype.name)
            else:
                content.append(dtype.name)
                
types = ["'"+"', '".join(container)+"'", "'"+"', '".join(content)+"'"]
t = ""
for x in content:
    t += "node.type like '"+x+"%' or "

for i in range(0,2):
    viewsql = "select nodemapping.nid AS nid,nodemapping.cid AS cid, node.type AS type from (nodemapping join node on((nodemapping.cid=node.id))) where (node.type in ("+types[i]+"))"    
    createView(dbname, viewnames[i], viewsql)
    
