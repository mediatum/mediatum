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
try:
    import sqlite3 as sqlite
except:
    from pysqlite2 import dbapi2 as sqlite
import core.tree as tree

from utils.utils import iso2utf8, esc
from schema.schema import node_getSearchFields



MAX_SEARCH_FIELDS = 32
DB_NAME = 'searchindex.db'
FULLTEXT_INDEX_MODE = 0

class SearchIndexer:

    def __init__(self):
        global MAX_SEARCH_FIELDS
        global DB_NAME
        global FULLTEXT_INDEX_MODE
    
        s = ''
        for i in range(1, MAX_SEARCH_FIELDS):
            s += 'field'+ str(i)+", "
        s = s[:-2]

        self.db = sqlite.connect(config.get("paths.searchstore") + DB_NAME, check_same_thread=False)
        self.cur = self.db.cursor()
        
        try:
            # simple search table
            self.cur.execute('CREATE VIRTUAL TABLE fullsearchmeta USING fts2(id, type, schema, value)')
            # extended search table
            self.cur.execute('CREATE VIRTUAL TABLE searchmeta USING fts2(id, type, schema, fieldnames, '+s+')')
            # fulltext search table
            self.cur.execute('CREATE VIRTUAL TABLE textsearchmeta USING fts2(id, type, schema, value)')
            
        except sqlite.OperationalError:
            print "searchdatabase already initialised"
        self.db.commit()
        
    def clearIndex(self):
        print "\nclearing index tables..."
        for table in ["fullsearchmeta", "fullsearchmeta_content", "fullsearchmeta_segdir", "fullsearchmeta_segments", 
                      "searchmeta", "searchmeta_content", "searchmeta_segdir", "searchmeta_segments",
                      "textsearchmeta", "textsearchmeta_content", "textsearchmeta_segdir", "textsearchmeta_segments"]:
            try:
                self.cur.execute("delete from "+ table)
            except:
                print " - table", table, "not found"
        self.db.commit()
        print "...cleared"
        
    def dropIndex(self):
        print "\ndropping index tables..."
        for table in ["fullsearchmeta", "fullsearchmeta_content", "fullsearchmeta_segdir", "fullsearchmeta_segments", 
                      "searchmeta", "searchmeta_content", "searchmeta_segdir", "searchmeta_segments",
                      "textsearchmeta", "textsearchmeta_content", "textsearchmeta_segdir", "textsearchmeta_segments"
                      ]:
            try:
                self.cur.execute("drop table "+table)
            except sqlite.OperationalError:
                print " - table", table, "not found"
        self.db.commit()
        print "...dropped"     
        
        
    def nodeToSimpleSearch(self, node):
        # build simple search index from node
        try:
            sql = 'INSERT INTO fullsearchmeta (id, type, schema, value) VALUES("'+ str(node.id)+'", "'+node.getType().type+'", "'+node.getType().metadatatypename+'", "'+ str(node.name) + '| '
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
        v_list = {}
        i = 1
        fieldnames = ''
        #for field in node.getType().getSearchFields():
        for node in node_getSearchFields(node):
            v_list[str(i)] = node.get(field.getName())
            fieldnames += field.getName() + '|'
            i+=1
        fieldnames = fieldnames[:-1]
            
        sql = 'INSERT INTO searchmeta (id, type, schema, fieldnames, '
        values = ''
        
        try:
            if len(v_list) > 0:
                for key in v_list:
                    sql += 'field'+str(key)+', '
                    values += '"'+iso2utf8(esc(v_list[key]))+ '", '
                sql = sql[:-2]
                values = values[:-2]
                sql = sql+') VALUES("'+ str(node.id)+'", "'+node.getType().type+'", "'+node.getType().metadatatypename+'", "'+fieldnames+'", ' + values + ')'
            else:
                sql = sql[:-2]
                sql = sql+') VALUES("'+ str(node.id)+'", "'+node.getType().type+'", "'+node.getType().metadatatypename+'", "'+fieldnames+'")'
            self.cur.execute(sql)
            return True
        except:
            return False
            
    """
        mode values:
            0: index fulltext without changes
            1: optimize fulltext (each word once)
            2: each word once with number of occurences
    """
    def nodeToFulltextSearch(self, node, mode=0):
        # build fulltext index from node
        
        if not node.getContentType()=="document":
            # only build fulltext of document nodes
            return True
        
        for file in node.getFiles():
            if file.getType() == "fulltext" and os.path.exists(file.getPath()):
                data = {}
                content = ''
                f = open(file.getPath())
                try:
                    for line in f:
                        if mode==0:
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

                if mode==1:
                    for key in data.keys():
                        content += key + " "
                elif mode==2:
                    for key in data.keys():
                        content += key + " ["+ str(data[key])+"] "

                if len(content)>0:
                    try:
                        sql = 'INSERT INTO textsearchmeta (id, type, schema, value) VALUES("'+str(node.id)+'", "'+str(node.getType().type)+'", "'+str(node.getType().metadatatypename)+'", "'+iso2utf8(esc(content))+'")'
                        self.cur.execute(sql)
                    except:
                        return False
                else:
                    print "no Content"
        return True
    
    def updateNode(self, node):
        self.removeNode(node)
        if not self.nodeToSimpleSearch(node):
            print "error updating simple search index for node", node.id
        if not self.nodeToExtSearch(node):
            print "error updating extended search index for node", node.id
        if not self.nodeToFulltextSearch(node):
            print "error updating fulltext search index for node", node.id
        self.db.commit()
        print "index updated for node", node.id

        
    def removeNode(self, node):
        for table in self.tablenames:
            self.cur.execute("DELETE FROM "+table+" WHERE id="+str(node.id))
        self.db.commit()
        print "node", node.id, "removed from index"
        
    def runIndexer(self):
        errorindexfull = []
        errorindexext = []
        errorindextext = []
        
        root = tree.getRoot()
        self.clearIndex()
        print "\nbuilding indices..."
        
        nodes=0
        for node in root.getAllChildren():
            if not self.nodeToSimpleSearch(node):
                errorindexfull.append(node.id)
                
            if not self.nodeToExtSearch(node):
                errorindexext.append(node.id)
 
            #if not self.nodeToFulltextSearch(node):
            #    errorindextext.append(node.id)              
            nodes+=1
        
        self.db.commit()
        print "  import of", nodes, "nodes finished with",len(errorindexfull)+len(errorindexext)+len(errorindextext), "error(s)."
        if len(errorindexfull)>0:
            print "   Simple Search Index:\n    error(s) in node with id:"
            for item in errorindexfull:
                print "    -", item
                
        if len(errorindexext)>0:
            print "   Extended Search Index:\n    error(s) in node with id:"
            for item in errorindexext:
                print "    -", item

        if len(errorindextext)>0:
            print "   Fulltext Search Index:\n    error(s) in node with id:"
            for item in errorindextext:
                print "    -", item
                
    def getDefForScheme(self, schema):
        res = self.cur.execute("SELECT fieldnames FROM searchmeta where schema='"+schema.getName()+"'")
        for item in res.fetchall():
            return item.split('|')
        
    
    
    
    def runQuery(self):
        #sql = "select id, field4 from searchmeta where type='image' and scheme='lt' and field4 < '2007-01-01T00:00:00' order by field4 desc"
        sql = "select id, field9 from searchmeta where type='document' and scheme='diss' and field9 < '2000' order by field9 desc"
        res = self.cur.execute(sql)
        for item in res.fetchall():
            print item
        

    def node_changed(self,node):
        index.updateNode(node)
        
        
    def searchfields_changed(self, node):
        #TODO 
        None


searchIndexer = SearchIndexer()

searchIndexer.runIndexer()



