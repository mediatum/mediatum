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
sys.path += ["../","."]
import re
import os
import core
import core.config as config
import core.tree as tree
from utils.utils import u, union
from math import ceil

DB_NAME = 'searchindex.db'
MAX_SEARCH_FIELDS = 32

"""
    0: index fulltext without changes
    1: optimize fulltext (each word once)
    2: each word once with number of occurences
"""
FULLTEXT_INDEX_MODE = 0

try:
    try:
        import sqlite3 as sqlite
    except:
        from pysqlite2 import dbapi2 as sqlite
except ImportError:
    print "\n\n\nImport Error:\nModule sqlite with fts3 support can not be found on the system, check your configuration.\n"
    sys.exit()

class FtsSearcher:

    def __init__(self):
        global DB_NAME
        self.db = sqlite.connect(config.get("paths.searchstore") + DB_NAME, check_same_thread=False)
        self.cur = self.db.cursor()
        self.tablenames = ["fullsearchmeta", "searchmeta", "textsearchmeta"]

    def run_search(self, field, op, value):
        ret = []
        if value=="" or field=="" or op=="":
            return []
           
        if field == "full": # all metadata incl. fulltext
            res = self.cur.execute('select distinct(id) from fullsearchmeta where fullsearchmeta match ?', ['\'value:'+protect(u(value))+ ' type:-directory\''])
            ret = [str(s[0]) for s in res.fetchall()]

            #fulltext
            res = self.cur.execute('select distinct(id) from textsearchmeta where textsearchmeta match ?', ['\'value:'+protect(u(value))+ ' type:-directory\''])
            retfull = [str(s[0]) for s in res.fetchall()]
            return union([ret, retfull])
            
        elif field == "fulltext": # fulltext
            res = self.cur.execute('select distinct(id) from textsearchmeta where textsearchmeta match ?', ['\'value:'+protect(u(value))+ ' type:-directory\''])
            return [str(s[0]) for s in res.fetchall()]
            
        elif field == "schema":
            res = self.cur.execute('select distinct(id) from fullsearchmeta where schema="'+u(value).replace("'","")+'"')
            return [str(s[0]) for s in res.fetchall()]
        
        elif field == "objtype":
            res = self.cur.execute('select distinct(id) from fullsearchmeta where type="'+u(value).replace("'","")+'"')
            ret = [str(s[0]) for s in res.fetchall()]
            return ret
            
        elif field == "updatetime":
            if len(value)==10:
                value +="T00:00:00"
            res = self.cur.execute('select distinct(id) from searchmeta where updatetime '+op+' "'+u(value)+'"')
            ret = [str(s[0]) for s in res.fetchall()]
            return ret

        else: # special search
            res = self.cur.execute('select position, name from searchmeta_def where attrname=?', [field])
            for pos in res.fetchall():
                if op in [">=","<="]:
                    res = self.cur.execute('select distinct(id) from searchmeta where schema="'+str(pos[1])+'" and field'+str(pos[0])+' '+op+' "'+str(value)+'"')                    
                else:
                    res = self.cur.execute('select distinct(id) from searchmeta where searchmeta match ?', ['field'+str(pos[0])+':'+protect(u(value))+ ' type:-directory'])
                
                res = [str(s[0]) for s in res.fetchall()]
                if len(ret)==0:
                    ret = res

                if len(res)>0:
                    ret = union([ret, res])
        return ret
  
    def query(self, q=""):
        from core.tree import searchParser
        p = searchParser.parse(q)
        return p.execute()
    
    def initIndexer(self, option=""):
        global MAX_SEARCH_FIELDS
        global DB_NAME
        global FULLTEXT_INDEX_MODE

        s = ''
        for i in range(1, MAX_SEARCH_FIELDS):
            s += 'field'+ str(i)+", "
        s = s[:-2]

        self.schemafields = {}

        #if option=="init":
        try:
            # simple search table
            self.cur.execute('CREATE VIRTUAL TABLE fullsearchmeta USING fts3(id, type, schema, value)')
            # extended search table
            self.cur.execute('CREATE VIRTUAL TABLE searchmeta USING fts3(id, type, schema, updatetime, '+s+')')
            self.cur.execute('CREATE VIRTUAL TABLE searchmeta_def USING fts3(name, position, attrname)')
            # fulltext search table
            self.cur.execute('CREATE VIRTUAL TABLE textsearchmeta USING fts3(id, type, schema, value)')
                   
        except sqlite.OperationalError:
            print "searchdatabase already initialised"
        self.db.commit()
    
    def getAllTableNames(self):
        ret = []
        for table in self.tablenames:
            ret.append(table)
            for table_add in ['content', 'segdir', 'segments']:
                ret.append(table+'_'+table_add)
        return ret
    
    
    def clearIndex(self):
        print "\nclearing index tables..."
        for table in self.getAllTableNames():
            try:
                self.cur.execute("delete from "+ table)
            except:
                print " - table", table, "not found"
        self.cur.execute("DELETE FROM searchmeta_def")
        self.db.commit()
        print "...cleared"
        
    def dropIndex(self):
        print "\ndropping index tables..."
        for table in self.getAllTableNames():
            try:
                self.cur.execute("drop table "+table)
            except sqlite.OperationalError:
                print " - table", table, "not found"
        self.db.commit()
        print "...dropped"
        
    def getDefForSchema(self, schema):
        ret = {}
        res = self.cur.execute('SELECT position, attrname FROM searchmeta_def WHERE name="'+str(schema)+'" ORDER BY position')
        
        for id, attr in res.fetchall():
            ret[id] = attr
        return ret

        
    def nodeToSimpleSearch(self, node):
        # build simple search index from node
        try:
            sql = 'INSERT INTO fullsearchmeta (id, type, schema, value) VALUES(\''+ str(node.id)+'\', \''+node.getContentType()+'\', \''+node.getSchema()+'\', \''+ str(node.name) + '| '
            # attributes
            for key,value in node.items():
                sql += protect(u(value))+'| '

            # files
            for file in node.getFiles():
                sql += protect(u(file.getName()+ '| '+file.getType()+'| '+file.getMimeType())+'| ')

            sql += '\')'
            self.cur.execute(sql)
            return True
        except:
            return False

            
    def nodeToExtSearch(self, node):
        # build extended search index from node
        if len(node.getSearchFields())==0:
            # stop if schema has no searchfields
            return True
            
        v_list = {}
        values = ''
        i = 1
        for field in node.getSearchFields():
            if field.getFieldtype()=="union":
                v_list[str(i)] = [field.get("valuelist").split(";")]
            else:
                v_list[str(i)] = node.get(field.getName())
            i+=1
            
        # save definition
        self.nodeToSchemaDef(node)
  
        sql = 'INSERT INTO searchmeta (id, type, schema, updatetime, '

        try:
            if len(v_list) > 0:
                for key in v_list:
                    if type(v_list[key])==list:
                        sub_s = ""
                        for item in v_list[key][0]:
                            sub_s += node.get(item)+" "
                            
                        sql += 'field'+str(key)+', '
                        values += '"'+u(sub_s)+ '", '
                    else:
                        sql += 'field'+str(key)+', '
                        values += '"'+u(v_list[key])+ '", '
                sql = sql[:-2]
                values = protect(values[:-2])
                sql = sql+') VALUES("'+ str(node.id)+'", "'+node.getContentType()+'", "'+node.getSchema()+'", "'+node.get("updatetime")+'", ' + values + ')'
            else:
                sql = sql[:-2]
                sql = sql+') VALUES("'+ str(node.id)+'", "'+node.getContentType()+'", "'+node.getSchema()+'", "'+node.get("updatetime")+'")'
            print sql
            self.cur.execute(sql)
            
            return True
        except:
            return False
      
      
    def nodeToSchemaDef(self, node):
        fieldnames = {}
        i = 1
        for field in node.getSearchFields():
            fieldnames[str(i)] = field.getName()
            i+=1

        self.cur.execute('DELETE FROM searchmeta_def WHERE name="' + node.getSchema()+'"')
        for id in fieldnames.keys():
            self.cur.execute('INSERT INTO searchmeta_def (name, position, attrname) VALUES("'+node.getSchema()+'", "'+id+'", "'+fieldnames[id]+'")')

    def nodeToFulltextSearch(self, node):
        # build fulltext index from node
        
        if not node.getContentType() in ("document", "dissertation"):
            # only build fulltext of document nodes
            return True
        r = re.compile("[a-zA-Z0-9]+")
        
        for file in node.getFiles():
            w = ''
            if file.getType() == "fulltext" and os.path.exists(file.retrieveFile()):
                data = {}
                content = ''
                f = open(file.retrieveFile())
                try:
                    for line in f:
                        if FULLTEXT_INDEX_MODE==0:
                            content += u(line)
                        else:
                            for w in re.findall(r, line):
                                if not w in data.keys():
                                    data[w] = 1
                            try:
                                data[w] += 1
                            except KeyError:
                                data[w] = 1
                finally:
                    f.close()

                if FULLTEXT_INDEX_MODE==1:
                    for key in data.keys():
                        content += key + " "
                elif FULLTEXT_INDEX_MODE==2:
                    for key in data.keys():
                        content += key + " ["+ str(data[key])+"] "
                        
                content = u(content.replace("'","").replace('"',""))
                if len(content)>0:
                    content_len = len(content)
                    p=0
                    
                    while p in range(0, int(ceil(content_len/500000.0))):
                        try:
                            self.cur.execute('INSERT INTO textsearchmeta (id, type, schema, value) VALUES("'+str(node.id)+'", "'+str(node.getContentType())+'", "'+str(node.getSchema())+'", "'+content[p*500000:(p+1)*500000-1]+'")')
                        except:
                            print "\nerror in fulltext of node",node.id
                            return False
                        p+=1
                return True
        return True
    
    
    def updateNodeIndex(self, node):
        #self.removeNodeIndex(node)
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
        try:
            self.db.commit()
        except:
            err['commit'].append(node.id)
        return err


    def updateNodesIndex(self, nodelist):
        print "\nupdating node index..."
        err = {}
        schemas = {}
        for node in nodelist:
            self.removeNodeIndex(node)
            sys.stdout.flush()
            print ".",
        print "\n...old index removed\n"
        for node in nodelist:
            sys.stdout.flush()
            print ".",
            try:
                if node.getSchema() not in schemas.keys():
                    schemas[node.getSchema()] = node
                err = self.updateNodeIndex(node)
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
    def removeNodeIndex(self, node, mode=0):
        for table in self.tablenames:
            self.cur.execute('DELETE FROM '+table+' WHERE id="'+str(node.id)+'"')
        try:
            self.db.commit()
        except:
            print "commit failed"
        if mode!=0:
            print "node", node.id, "removed from index"
    

    def reindex(self, option="", nodelist=None):
        err = []
        if not nodelist:
            nodes = tree.getRoot().getAllChildren()
        else:
            nodes = nodelist
        self.initIndexer(option)
        err = self.updateNodesIndex(nodes)
        print err
        
    def node_changed(self, node):
        print "node_change fts3"
        self.updateNodesIndex([node])
     
    
ftsSearcher = FtsSearcher()
def protect(s):
    return s.replace('\'','"')
    
def subnodes(node):
    return node.getAllChildren().getIDs()
