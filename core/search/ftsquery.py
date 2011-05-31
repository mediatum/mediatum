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
from utils.utils import u, union, formatException, normalize_utf8, OperationException
from utils.date import format_date
from math import ceil

import core.db.sqliteconnector as sqlite

log = logging.getLogger("backend")

DB_NAME_STD = 'searchindex.db' # only 1 database
DB_NAME_FULL = 'searchindex_full.db' # database for simple search
DB_NAME_EXT = 'searchindex_ext.db' # database for extended search
DB_NAME_TEXT = 'searchindex_text.db' # database for fulltext search
MAX_SEARCH_FIELDS = 32

"""
    0: index fulltext without changes
    1: optimize fulltext (each word once)
    2: each word once with number of occurences
"""
FULLTEXT_INDEX_MODE = 0
DBTYPE = 'std' #'std|split'   split = split databases; std = all tables in one db

class FtsSearcher:
    def __init__(self):
        global DBTYPE
        self.connames = {'std':{'full':'std', 'ext':'std', 'text':'std'},
                                'split':{'full':'full', 'ext':'ext', 'text':'text'}}
        self.tablenames = {'full':"fullsearchmeta", 'ext':"searchmeta", 'text':"textsearchmeta"}
        self.db = {}
        
        if DBTYPE not in self.connames.keys():
            raise OperationException("error in search definition")
        
        for conname in self.connames[DBTYPE]:
            if self.connames[DBTYPE][conname] not in self.db.keys():
                self.db[self.connames[DBTYPE][conname]] = sqlite.SQLiteConnector("%s%s" %(config.get("paths.searchstore"), eval('DB_NAME_'+(self.connames[DBTYPE][conname]).upper())))
        self.normalization_items = None

    def run_search(self, field, op, value):
        
        def getSQL(type, value, spc ={}): # deliver sql for given type
            value = normalize_utf8(protect(u(value)))
            
            if type=="full": # all metadata
                return 'select distinct(id) from fullsearchmeta where fullsearchmeta match \'value:'+value+'\' and type <>\'directory\''
            elif type=="fulltext": # fulltext
                return 'select distinct(id) from textsearchmeta where textsearchmeta match \'value:'+value+'\' and type<>\'directory\''
            elif type=="schema": # schemadef
                return 'select distinct(id) from fullsearchmeta where schema="'+value.replace("'","")+'"'
            elif type=="objtype": # object type
                return 'select distinct(id) from fullsearchmeta where type="'+value.replace("'","")+'"'
            elif type=="updatetime": # update time with operator <|>|=
                if len(value)==10:
                    value +="T00:00:00"
                return 'select distinct(id) from searchmeta where updatetime '+spc['op']+' "'+value+'"'
            elif type=="field":
                return 'select position, name from searchmeta_def where attrname=\''+value+'\''
            elif type=="spcompare":
                return 'select distinct(id) from searchmeta where schema="'+str(spc['pos'][1])+'" and field'+str(spc['pos'][0])+' '+spc['op']+' "'+value+'"'
            elif type=="spfield":
                return 'select distinct(id) from searchmeta where field'+str(spc['pos'][0])+'=""'
            elif type=="spmatch":
                return 'select distinct(id) from searchmeta where field'+str(spc['pos'][0])+' match \''+value+'\' and type <> \'directory\''
            
        
        global DBTYPE
        ret = []
        if value=="" or field=="" or op=="":
            return []
            
        if field=="full": # all metadata incl. fulltext
            res1 = self.execute(getSQL("full", value), self.connames[DBTYPE]['full']) # all metadata
            res2 = self.execute(getSQL("fulltext", value), self.connames[DBTYPE]['text']) # fulltext
            return union([[str(s[0]) for s in res1], [str(s[0]) for s in res2]])
            
        elif field=="fulltext": # fulltext
            return [str(s[0]) for s in self.execute(getSQL("fulltext", value), self.connames[DBTYPE]['text'])]
            
        elif field=="allmetadata": # all metadata 
            return [str(s[0]) for s in self.execute(getSQL("full", value), self.connames[DBTYPE]['full'])] 
            
        elif field=="schema":
            return [str(s[0]) for s in self.execute(getSQL("schema", value), self.connames[DBTYPE]['full'])]
        
        elif field=="objtype":
            return [str(s[0]) for s in self.execute(getSQL("objtype", value), self.connames[DBTYPE]['full'])]

        elif field=="updatetime":
            return [str(s[0]) for s in self.execute(getSQL("updatetime", value, spc={'op':op}), self.connames[DBTYPE]['ext'])]

        else: # special search
            for pos in self.execute(getSQL("field", field), self.connames[DBTYPE]['ext']):
                if op in [">=","<="]:
                    res = self.execute(getSQL("spcompare", value, spc={'op':op, 'pos':pos}), self.connames[DBTYPE]['ext'])
                else:
                    if value=="''":
                        res = self.execute(getSQL("spfield", spc={'pos':str(pos)}), self.connames[DBTYPE]['ext'])
                    else:
                        res = self.execute(getSQL("spmatch", value, spc={'pos':pos}), self.connames[DBTYPE]['ext'])

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
        global DBTYPE, MAX_SEARCH_FIELDS 

        def create(sql, type):
            try:
                self.execute(sql, type)
            except:
                e = sys.exc_info()[1]
                if "already exists" not in str(e):
                    raise

        if option=="init":
            # simple search table
            create('CREATE VIRTUAL TABLE fullsearchmeta USING fts3(id, type, schema, value)', self.connames[DBTYPE]['full'])
            # extended search table
            create('CREATE VIRTUAL TABLE searchmeta USING fts3(id, type, schema, updatetime, '+", ".join(['field'+str(i) for i in range(1, MAX_SEARCH_FIELDS)])+')', self.connames[DBTYPE]['ext'])
            create('CREATE VIRTUAL TABLE searchmeta_def USING fts3(name, position, attrname)', self.connames[DBTYPE]['ext'])
            # fulltext search table
            create('CREATE VIRTUAL TABLE textsearchmeta USING fts3(id, type, schema, value)', self.connames[DBTYPE]['text'])

    
    def getAllTableNames(self):
        ret = {'full':[], 'ext':[], 'text':[]}
        for type in self.tablenames:
            ret.append(self.tablenames[type])
            for table_add in ['content', 'segdir', 'segments']:
                ret.append(self.tablenames[type]+'_'+table_add)
        return ret
    
    
    def clearIndex(self):
        global DBTYPE
        print "\nclearing index tables..."
        all_tables = self.getAllTableNames()
        for type in all_tables:
            for table in all_tables[type]:
                try:
                    self.execute('DELETE FROM '+table, self.connames[DBTYPE][type])
                except:
                    pass
        try:
            self.execute('DELETE FROM searchmeta_def', self.connames[DBTYPE]['ext'])
        except:
            pass
        print "...cleared"
        
        
    def dropIndex(self):
        global DBTYPE
        print "\ndropping index tables..."
        all_tables = self.getAllTableNames()
        for type in all_tables:
            for table in all_tables[type]:
                try:
                    self.execute('DROP TABLE '+table, self.connames[DBTYPE][type])
                except:
                    pass
        try:
            self.execute('DROP TABLE searchmeta_def', self.connames[DBTYPE]['ext'])
        except:
            pass
        print "...dropped"
        
    def getDefForSchema(self, schema):
        global DBTYPE
        ret = {}
        for id, attr in self.execute('SELECT position, attrname FROM searchmeta_def WHERE name="'+str(schema)+'" ORDER BY position', self.connames[DBTYPE]['ext']):
            ret[id] = attr
        return ret

    def execute(self, sql, type='std'):
        try:
            return self.db[type].execute(sql)
        except:
            print "error in search indexer operation"
            #self.initIndexer('init')
            #return self.db[type].execute(sql)
       
    def nodeToSimpleSearch(self, node, type=""): # build simple search index from node
        global DBTYPE
        if type=="":
            type = DBTYPE # use definition
        
        sql_upd = 'UPDATE fullsearchmeta SET type = \''+node.getContentType()+'\', schema=\''+node.getSchema()+'\', value=\''+ str(node.name) + '| '
        sql_ins = 'INSERT INTO fullsearchmeta (id, type, schema, value) VALUES(\''+ str(node.id)+'\', \''+node.getContentType()+'\', \''+node.getSchema()+'\', \''+ str(node.name) + '| '
        
        # attributes
        val = ''
        for key,value in node.items():
            val += protect(u(value))+'| '
        for v in val.split(" "):
            v = u(v)
            if normalize_utf8(v)!=v.lower():
                val += ' '+normalize_utf8(v)
                
        val = val.replace(chr(0), "") + ' '
  
        # files
        for file in node.getFiles():
            val += protect(u(file.getName()+ '| '+file.getType()+'| '+file.getMimeType())+'| ')

        sql_upd += val +'\' WHERE id=\''+node.id+'\''
        sql_ins += val +'\')'

        sql = ""
        try:
            sql = 'SELECT id from fullsearchmeta WHERE id=\''+node.id+'\''
            if self.execute(sql, self.connames[type]['full']): # check existance
                sql = sql_upd # do update
            else:
                sql = sql_ins # do insert
            self.execute(sql, self.connames[type]['full'])
            return True
        except:
            logException('error in sqlite insert/update: '+sql)
            return False

            
    def nodeToExtSearch(self, node, type=""): # build extended search index from node
        global DBTYPE
        if type=="":
            type = DBTYPE # use definition
        
        if len(node.getSearchFields())==0: # stop if schema has no searchfields
            return True

        self.nodeToSchemaDef(node) # save definition
 
        keyvalue = []
        i = 1
        for field in node.getSearchFields():
            key = "field%d" % i
            i += 1
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
            if self.execute(sql0, self.connames[type]['ext']): #select
                sql = sql1
                self.execute(sql1, self.connames[type]['ext']) # do update
            else:
                sql = sql2
                self.execute(sql2, self.connames[type]['ext']) # do insert
            return True
        except:
            logException('error in sqlite insert/update: '+sql)
            return False
      
      
    def nodeToSchemaDef(self, node, type=""): # update schema definition
        global DBTYPE
        if type=="":
            type = DBTYPE # use definition
        
        fieldnames = {}
        i = 1
        for field in node.getSearchFields():
            fieldnames[str(i)] = field.getName()
            i += 1

        self.execute('DELETE FROM searchmeta_def WHERE name="' + node.getSchema()+'"', self.connames[type]['ext'])
        for id in fieldnames.keys():
            self.execute('INSERT INTO searchmeta_def (name, position, attrname) VALUES("'+node.getSchema()+'", "'+id+'", "'+fieldnames[id]+'")', self.connames[type]['ext'])

    def nodeToFulltextSearch(self, node, type=""): # build fulltext index from node
        global DBTYPE
        if type=="":
            type = DBTYPE # use definition
        
        if not node.getCategoryName()=="document": # only build fulltext of document nodes
            return True
        r = re.compile("[a-zA-Z0-9]+")
       
        if self.execute('SELECT id from textsearchmeta where id=\''+node.id+'\'', self.connames[type]['text']):
            # FIXME: we should not delete the old textdata from this node, and insert
            # the new files. Only problem is, DELETE from a FTS3 table is prohibitively
            # slow.
            return
        
        for file in node.getFiles():
            w = ''
            if file.getType()=="fulltext" and os.path.exists(file.retrieveFile()):
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
                    p = 0
                    
                    while p in range(0, int(ceil(content_len/500000.0))):
                        sql = 'INSERT INTO textsearchmeta (id, type, schema, value) VALUES("'+str(node.id)+'", "'+str(node.getContentType())+'", "'+str(node.getSchema())+'", "'+normalize_utf8((content[p*500000:(p+1)*500000-1]))+'")'
                        try:
                            self.execute(sql, self.connames[type]['text'])
                        except:
                            print "\nerror in fulltext of node",node.id
                            return False
                        p += 1
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

        t2 = time.time()
        for key in schemas:
            self.nodeToSchemaDef(schemas[key])
        #print "%f seconds for adding new index" % (t2-t1)
        #print "%f seconds for updating schema definitions" % (time.time()-t2)
        return err
   
    
    """
        mode:
            0: no printout
    """
    def removeNodeIndex(self, node, mode=0):
        global DBTYPE
        for type in self.tablenames:
            for table in self.tablesnames[type]:
                try:
                    self.execute('DELETE FROM '+table+' WHERE id="'+node.id+'"', self.connames[DBTYPE][type])
                except:
                    pass
        if mode!=0:
            print "node", node.id, "removed from index"


    def reindex(self, nodelist):
        for node in nodelist:
            node.setDirty()
        
    def node_changed(self, node):
        print "node_change fts3",node.id
        node.setDirty()
        
    def getSearchInfo(self):
        global DBTYPE
        ret = []
        key = ["sqlite_type", "sqlite_name", "sqlite_tbl_name", "sqlite_rootpage", "sqlite_sql"]
        for type in self.connames[DBTYPE]:
            for table in self.execute("SELECT * FROM sqlite_master", self.connames[DBTYPE][type]):
                i = 0
                t = []
                for item in table:
                    t.append((key[i],item))
                    i += 1
                if t[0][1]=="table":
                    items = self.execute("SELECT count(*) FROM "+t[2][1], self.connames[DBTYPE][type])
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

