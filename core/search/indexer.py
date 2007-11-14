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

import re
import os
import core
import core.config as config
import core.tree as tree

try:
    import sqlite3 as sqlite
except:
    try:
        from pysqlite2 import dbapi2 as sqlite
    except:
        pass # skip this import for now
import core.tree as tree

from utils.utils import iso2utf8, esc

MAX_SEARCH_FIELDS = 32
DB_NAME = 'searchindex.db'
FULLTEXT_INDEX_MODE = 1

class SearchIndexer:

    def __init__(self):
        global MAX_SEARCH_FIELDS
        global DB_NAME
        global FULLTEXT_INDEX_MODE
        
        self.tablenames = ["fullsearchmeta", "searchmeta", "textsearchmeta"]
    
        s = ''
        for i in range(1, MAX_SEARCH_FIELDS):
            s += 'field'+ str(i)+", "
        s = s[:-2]

        self.db = sqlite.connect(config.get("paths.searchstore") + DB_NAME, check_same_thread=False)
        self.cur = self.db.cursor()
        
        self.schemafields = {}
        
        try:
            # simple search table
            self.cur.execute('CREATE VIRTUAL TABLE fullsearchmeta USING fts2(id, type, schema, value)')
            # extended search table
            self.cur.execute('CREATE VIRTUAL TABLE searchmeta USING fts2(id, type, schema, '+s+')')
            self.cur.execute('CREATE VIRTUAL TABLE searchmeta_def USING fts2(name, position, attrname)')
            # fulltext search table
            self.cur.execute('CREATE VIRTUAL TABLE textsearchmeta USING fts2(id, type, schema, value)')
            
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
            sql = 'INSERT INTO fullsearchmeta (id, type, schema, value) VALUES("'+ str(node.id)+'", "'+node.getContentType()+'", "'+node.getSchema()+'", "'+ str(node.name) + '| '
            # attributes
            for key,value in node.items():
                sql += str(esc(iso2utf8(value)))+'| '

            # files
            for file in node.getFiles():
                sql += str(esc(iso2utf8(file.getName()+ '| '+file.getType()+'| '+file.getMimeType())))+'| '

            sql = iso2utf8(sql+'")')
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
        i = 1
        for field in node_getSearchFields(node):
            v_list[str(i)] = node.get(field.getName())
            i+=1
        
        # save definition
        self.nodeToSchemaDef(node)
            
        sql = 'INSERT INTO searchmeta (id, type, schema, '
        values = ''
        try:
            if len(v_list) > 0:
                for key in v_list:
                    sql += 'field'+str(key)+', '
                    values += '"'+iso2utf8(esc(v_list[key]))+ '", '
                sql = sql[:-2]
                values = values[:-2]
                sql = sql+') VALUES("'+ str(node.id)+'", "'+node.getContentType()+'", "'+node.getSchema()+'", ' + values + ')'
            else:
                sql = sql[:-2]
                sql = sql+') VALUES("'+ str(node.id)+'", "'+node.getContentType()+'", "'+node.getSchema()+'")'
            self.cur.execute(sql)
            return True
        except:
            return False
      
      
    def nodeToSchemaDef(self, node):
        fieldnames = {}
        i = 1
        for field in node_getSearchFields(node):
            fieldnames[str(i)] = field.getName()
            i+=1

        sql = 'DELETE FROM searchmeta_def WHERE name="' + node.getSchema()+'"'
        self.cur.execute(sql)
        for id in fieldnames.keys():
            sql = 'INSERT INTO searchmeta_def (name, position, attrname) VALUES("'+node.getSchema()+'", "'+id+'", "'+fieldnames[id]+'")'
            self.cur.execute(sql)
            
        
            
    """
        FULLTEXT_INDEX_MODE values:
            0: index fulltext without changes
            1: optimize fulltext (each word once)
            2: each word once with number of occurences
    """
    def nodeToFulltextSearch(self, node):
        # build fulltext index from node
        
        if not node.getContentType()=="document":
            # only build fulltext of document nodes
            return True
        r = re.compile("[a-zA-Z0-9äöüÄÖÜ]+")
        
        for file in node.getFiles():
            w = ''
            if file.getType() == "fulltext" and os.path.exists(file.getPath()):
                data = {}
                content = ''
                f = open(file.getPath())
                try:
                    for line in f:
                        if FULLTEXT_INDEX_MODE==0:
                            content += line
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
                sql = ""
                if len(content)>0:
                    try:
                        sql = 'INSERT INTO textsearchmeta (id, type, schema, value) VALUES("'+str(node.id)+'", "'+str(node.getContentType())+'", "'+str(node.getSchema())+'", "'+iso2utf8(esc(content))+'")'
                        self.cur.execute(sql)
                    except:
                        print "error", node.id,"\n"
                        return False
                else:
                    print "no Content"
        return True
    
    
    def updateNode(self, node):
        self.removeNode(node)
        err = {}
        err['simple'] = []
        err['ext'] = []
        err['text'] = []

        if not self.nodeToSimpleSearch(node):
            err['simple'].append(node.id)
        if not self.nodeToExtSearch(node):
            err['ext'].append(node.id)
        if not self.nodeToFulltextSearch(node):
            err['text'].append(node.id)
        self.db.commit()
        return err


    def updateNodes(self, nodelist):
        print "\nupdating node index..."
        err = {}
        schemas = {}
        for node in nodelist:
            try:
                if node.getSchema() not in schemas.keys():
                    schemas[node.getSchema()] = node
                err = self.updateNode(node)
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
    def removeNode(self, node, mode=0):
        for table in self.tablenames:
            self.cur.execute("DELETE FROM "+table+" WHERE id="+str(node.id))
        self.db.commit()
        if mode!=0:
            print "node", node.id, "removed from index"

    def runIndexer(self):
        err = []
        root = tree.getRoot()
        err = self.updateNodes(root.getAllChildren())
        print err

    def runQuery(self):
        #sql = "select id, field4 from searchmeta where type='image' and schema='lt' and field4 < '2007-01-01T00:00:00' order by field4 desc"
        sql = "select id, field9 from searchmeta where type='document' and schema='diss' and field9 < '2000' order by field9 desc"
        res = self.cur.execute(sql)
        for item in res.fetchall():
            print item
        

    def node_changed(self,node):
        index.updateNode(node)
        
        
    def searchfields_changed(self, node):
        #TODO 
        None

    
searchIndexer = SearchIndexer()

if __name__ == "__main__":
    searchIndexer.runIndexer()
    #print searchIndexer.getDefForSchema("hb")




