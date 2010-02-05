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
import thread
import time
import core
import core.config as config
import core.tree as tree
import logging
from utils.log import logException
from utils.utils import u, union, formatException, normalize_utf8
from utils.date import format_date
from math import ceil

import core.db.sqliteconnector as sqlite

log = logging.getLogger("backend")

DB_NAME = 'searchindex.db'
MAX_SEARCH_FIELDS = 32

"""
    0: index fulltext without changes
    1: optimize fulltext (each word once)
    2: each word once with number of occurences
"""
FULLTEXT_INDEX_MODE = 0

class FtsSearcher:
    def __init__(self):
        global DB_NAME
        self.db = sqlite.SQLiteConnector(config.get("paths.searchstore") + DB_NAME)
        self.tablenames = ["fullsearchmeta", "searchmeta", "textsearchmeta"]
        self.normalization_items = None

    def run_search(self, field, op, value):
        ret = []
        ret = []
        if value=="" or field=="" or op=="":
            return []
           
        if field == "full": # all metadata incl. fulltext
            res = self.db.execute('select distinct(id) from fullsearchmeta where fullsearchmeta match ?', ['\'value:'+normalize_utf8(protect(u(value)))+ ' type:-directory\''])
            ret = [str(s[0]) for s in res]

            #fulltext
            res = self.db.execute('select distinct(id) from textsearchmeta where textsearchmeta match ?', ['\'value:'+normalize_utf8((protect(u(value))))+ ' type:-directory\''])
            retfull = [str(s[0]) for s in res]
            return union([ret, retfull])
            
        elif field == "fulltext": # fulltext
            res = self.db.execute('select distinct(id) from textsearchmeta where textsearchmeta match ?', ['\'value:'+normalize_utf8(protect(u(value)))+ ' type:-directory\''])
            return [str(s[0]) for s in res]
            
        elif field == "schema":
            res = self.db.execute('select distinct(id) from fullsearchmeta where schema="'+normalize_utf8((u(value).replace("'","")))+'"')
            return [str(s[0]) for s in res]
        
        elif field == "objtype":
            res = self.db.execute('select distinct(id) from fullsearchmeta where type="'+normalize_utf8((u(value).replace("'","")))+'"')
            ret = [str(s[0]) for s in res]
            return ret
            
        elif field == "updatetime":
            if len(value)==10:
                value +="T00:00:00"
            res = self.db.execute('select distinct(id) from searchmeta where updatetime '+op+' "'+u(value)+'"')
            ret = [str(s[0]) for s in res]
            return ret

        else: # special search
            res = self.db.execute('select position, name from searchmeta_def where attrname=?', [field])
            for pos in res:
                if op in [">=","<="]:
                    res = self.db.execute('select distinct(id) from searchmeta where schema="'+str(pos[1])+'" and field'+str(pos[0])+' '+op+' "'+str(value)+'"')                    
                else:
                    if value=="''":
                        res = self.db.execute('select distinct(id) from searchmeta where field'+str(pos[0])+'=""')
                    else:
                        res = self.db.execute('select distinct(id) from searchmeta where searchmeta match ?', ['field'+str(pos[0])+':'+normalize_utf8(protect(u(value)))+ ' type:-directory'])
                
                res = [str(s[0]) for s in res]
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

        def create(sql):
            try:
                self.db.execute(sql)
            except:
                e = sys.exc_info()[1]
                if "already exists" not in str(e):
                    raise

        if option=="init":
            # simple search table
            create('CREATE VIRTUAL TABLE fullsearchmeta USING fts3(id, type, schema, value)')
            # extended search table
            create('CREATE VIRTUAL TABLE searchmeta USING fts3(id, type, schema, updatetime, '+s+')')
            create('CREATE VIRTUAL TABLE searchmeta_def USING fts3(name, position, attrname)')
            # fulltext search table
            create('CREATE VIRTUAL TABLE textsearchmeta USING fts3(id, type, schema, value)')

    
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
                self.execute("delete from "+ table)
            except:
                print " - table", table, "not found"
        self.execute("DELETE FROM searchmeta_def")
        print "...cleared"
        
    def dropIndex(self):
        print "\ndropping index tables..."
        for table in self.getAllTableNames():
            try:
                self.execute("drop table "+table)
            except sqlite.OperationalError:
                print " - table", table, "not found"
        print "...dropped"
        
    def getDefForSchema(self, schema):
        ret = {}
        res = self.db.execute('SELECT position, attrname FROM searchmeta_def WHERE name="'+str(schema)+'" ORDER BY position')
        
        for id, attr in res:
            ret[id] = attr
        return ret

    def execute(self, sql):
        return self.db.execute(sql)
        
    def nodeToSimpleSearch(self, node):
        # build simple search index from node
        
        sql0 = 'SELECT id from fullsearchmeta WHERE id=\''+node.id+'\''
        sql1 = 'UPDATE fullsearchmeta SET type = \''+node.getContentType()+'\', schema=\''+node.getSchema()+'\', value=\''+ str(node.name) + '| '
        sql2 = 'INSERT INTO fullsearchmeta (id, type, schema, value) VALUES(\''+ str(node.id)+'\', \''+node.getContentType()+'\', \''+node.getSchema()+'\', \''+ str(node.name) + '| '
        # attributes
        val = ''
        
        for key,value in node.items():
            val += protect(u(value))+'| '
        for v in val.split(" "):
            v = u(v)
            if normalize_utf8(v)!=v.lower():
                val += ' '+normalize_utf8(v)
                
        val = val.replace(chr(0),"")
        
        sql1 += val+ ' '
        sql2 += val+ ' '
            
        # files
        for file in node.getFiles():
            sql1 += protect(u(file.getName()+ '| '+file.getType()+'| '+file.getMimeType())+'| ')
            sql2 += protect(u(file.getName()+ '| '+file.getType()+'| '+file.getMimeType())+'| ')

        sql1 += '\' WHERE id=\''+node.id+'\''
        sql2 += '\')'

        sql = ""
        try:
            sql = sql0
            if self.execute(sql0): # select
                sql = sql1
                self.execute(sql1) # do update
            else:
                sql = sql2
                self.execute(sql2) # do insert
            return True
        except:
            logException('error in sqlite insert/update: '+sql)
            return False

            
    def nodeToExtSearch(self, node):
        # build extended search index from node
        if len(node.getSearchFields())==0:
            # stop if schema has no searchfields
            return True
            
        # save definition
        self.nodeToSchemaDef(node)
 
        keyvalue = []
        i = 1
        for field in node.getSearchFields():
            key = "field%d" % i
            i = i + 1
            value = ""
            if field.getFieldtype()=="union":
                for item in field.get("valuelist").split(";"):
                    value += node.get(item) + '|'
            else:
                value = node.get(field.getName())
            keyvalue += [(key, u(protect(value)))]
            
        sql0 = 'SELECT id FROM searchmeta where id=\''+node.id+'\''
        sql1 = 'UPDATE searchmeta SET '
        sql2 = 'INSERT INTO searchmeta (id, type, schema, updatetime'
        for key,value in keyvalue:
            sql1 += key + "='"+normalize_utf8(value)+"', "
            sql2 += ", "
            sql2 += key
        sql1 += "type='"+node.getContentType()+"', schema='"+node.getSchema()+"', updatetime='"+node.get("updatetime")+"'"
        sql2 += ") VALUES("
        sql2 += "'"+str(node.id)+"', \""+node.getContentType()+'", "'+node.getSchema()+'", "'+node.get("updatetime")+'"'
        for key,value in keyvalue:
            sql2 += ", '" + normalize_utf8(value) + "'"
        sql1 += " WHERE id='"+node.id+"'"
        sql2 += ")"

        sql = ""
        try:
            sql = sql0
            if self.execute(sql0): #select
                sql = sql1
                self.execute(sql1) # do update
            else:
                sql = sql2
                self.execute(sql2) # do insert
            return True
        except:
            logException('error in sqlite insert/update: '+sql)
            return False
      
      
    def nodeToSchemaDef(self, node):
        fieldnames = {}
        i = 1
        for field in node.getSearchFields():
            fieldnames[str(i)] = field.getName()
            i+=1

        self.execute('DELETE FROM searchmeta_def WHERE name="' + node.getSchema()+'"')
        for id in fieldnames.keys():
            self.execute('INSERT INTO searchmeta_def (name, position, attrname) VALUES("'+node.getSchema()+'", "'+id+'", "'+fieldnames[id]+'")')

    def nodeToFulltextSearch(self, node):
        # build fulltext index from node
        
        if not node.getContentType() in ("document", "dissertation"):
            # only build fulltext of document nodes
            return True
        r = re.compile("[a-zA-Z0-9]+")
       
        if self.execute('SELECT id from textsearchmeta where id=\''+node.id+'\''):
            # FIXME: we should not delete the old textdata from this node, and insert
            # the new files. Only problem is, DELETE from a FTS3 table is prohibitively
            # slow.
            return
        
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
                            self.execute('INSERT INTO textsearchmeta (id, type, schema, value) VALUES("'+str(node.id)+'", "'+str(node.getContentType())+'", "'+str(node.getSchema())+'", "'+normalize_utf8((content[p*500000:(p+1)*500000-1]))+'")')
                        except:
                            print "\nerror in fulltext of node",node.id
                            return False
                        p+=1
                return True
        return True
    
    
    def updateNodeIndex(self, node):
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
        node.set("updatesearchindex", str(format_date()))
        return err


    def updateNodesIndex(self, nodelist):
        print "updating node index for",len(nodelist),"nodes..."

        err = {}
        schemas = {}
        t1 = time.time()
        t2 = time.time()
        for node in nodelist:
            try:
                if node.getSchema() not in schemas.keys():
                    schemas[node.getSchema()] = node
                err = self.updateNodeIndex(node)
            except core.tree.NoSuchNodeError:
                # we ignore this exception, and mark the node
                # non-dirty anyway, to prevent it from blocking
                # updates of other nodes
                logException('error during updating '+str(node.id))
                print "error for id", node.id
            node.cleanDirty()

        t3 = time.time()
        for key in schemas:
            self.nodeToSchemaDef(schemas[key])
        t4 = time.time()
        print "%f seconds for removing old index" % (t2-t1)
        print "%f seconds for adding new index" % (t3-t2)
        print "%f seconds for updating schema definitions" % (t4-t3)
        return err
   
    
    """
        mode:
            0: no printout
    """
    def removeNodeIndex(self, node, mode=0):
        for table in self.tablenames:
            self.execute('DELETE FROM '+table+' WHERE id="'+str(node.id)+'"')
        if mode!=0:
            print "node", node.id, "removed from index"
    

    def reindex(self, nodelist):
        for node in nodelist:
            node.setDirty()
        
    def node_changed(self, node):
        print "node_change fts3",node.id
        node.setDirty()
        
    def getSearchInfo(self):
        ret = []
        key = ["sqlite_type", "sqlite_name", "sqlite_tbl_name", "sqlite_rootpage", "sqlite_sql"]
        res = self.db.execute("select * from sqlite_master")
        for table in res:
            i=0
            t = []
            for item in table:
                t.append((key[i],item))
                i += 1
            if t[0][1]=="table":
                items = self.db.execute("select count(*) from "+t[2][1])
                for item in items:
                    t.append(("sqplite_items_count",str(item[0])))
            ret.append(t)
        return ret
        
    def getSearchSize(self):
        import os
        return os.stat(config.settings["paths.searchstore"]+"searchindex.db")[6]

     
    
ftsSearcher = FtsSearcher()
ftsSearcher.initIndexer()

def protect(s):
    return s.replace('\'','"')
    
    
def subnodes(node):
    return node.getAllChildren().getIDs()

def fts_indexer_thread():
    if not time:
        return
    while 1:
        time.sleep(3)
        dirty = tree.getDirtyNodes(10)
        if dirty:
            ftsSearcher.updateNodesIndex(dirty)

def startThread():
    thread_id = thread.start_new_thread(fts_indexer_thread, ())
    log.info("started indexer thread, thread_id="+str(thread_id))

