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

import core.startup
import core.config as config
import sqlite3 as sqlite
import core.tree as tree

from utils.utils import iso2utf8, esc



MAX_SEARCH_FIELDS = 32
DB_NAME = 'searchindex.db'

class DbIndexer:

    def __init__(self):
        global MAX_SEARCH_FIELDS
        global DB_NAME
    
        s = ''
        for i in range(1, MAX_SEARCH_FIELDS):
            s += 'field'+ str(i)+", "
        s = s[:-2]

        self.db = sqlite.connect(config.get("paths.searchstore") + DB_NAME, check_same_thread=False)
        self.cur = self.db.cursor()
        
        try:
            # simple search table
            self.cur.execute('CREATE VIRTUAL TABLE fullsearchmeta USING fts2(id, type, scheme, value)')
            
            # extended search table
            self.cur.execute('CREATE VIRTUAL TABLE searchmeta USING fts2(id, type, scheme, fieldnames, '+s+')')
            
        except sqlite.OperationalError:
            print "searchdatabase already initialised"
        self.db.commit()
        
    def clearIndex(self):
        print "\nclearing index tables..."
        for table in ["fullsearchmeta", "fullsearchmeta_content", "fullsearchmeta_segdir", "fullsearchmeta_segments", 
                      "searchmeta", "searchmeta_content", "searchmeta_segdir", "searchmeta_segments"]:
            try:
                self.cur.execute("delete from "+ table)
            except:
                print " - table", table, "not found"
        self.db.commit()
        print "...cleared"
        
    def dropIndex(self):
        print "\ndropping index tables..."
        for table in ["fullsearchmeta", "fullsearchmeta_content", "fullsearchmeta_segdir", "fullsearchmeta_segments", 
                      "searchmeta", "searchmeta_content", "searchmeta_segdir", "searchmeta_segments"]:
            try:
                self.cur.execute("drop table "+table)
            except sqlite.OperationalError:
                print " - table", table, "not found"
        self.db.commit()
        print "...dropped"

    def indexNode(self, node):
        None
        
        
        
    def nodeToSimpleSearch(self, node):
        # build simple search index from node
        try:
            sql = 'INSERT INTO fullsearchmeta (id, type, scheme, value) VALUES("'+ str(node.id)+'", "'+node.getType().type+'", "'+node.getType().metadatatypename+'", "'+ str(node.name) + '| '
            # attributes
            for attr in node.items():
                sql += str(esc(iso2utf8(attr[1])))+'| '

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
        for field in node.getType().getSearchFields():
            v_list[str(i)] = node.get(field.getName())
            fieldnames += field.getName() + '|'
            i+=1
        fieldnames = fieldnames[:-1]
            
        sql = 'INSERT INTO searchmeta (id, type, scheme, fieldnames, '
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
    
    
    
        
    def runIndexer(self):
        errorindexfull = []
        errorindexext = []
        
        root = tree.getRoot()
        self.clearIndex()
        print "\nbuilding indices..."
        
        nodes=0
        for node in root.getAllChildren():
            if not self.nodeToSimpleSearch(node):
                errorindexfull.append(node.id)
                
            if not self.nodeToExtSearch(node):
                errorindexext.append(node.id)
 
            nodes+=1
        
        self.db.commit()
        print "  import of", nodes, "nodes finished with",len(errorindexfull)+len(errorindexext), "error(s)."
        if len(errorindexfull)>0:
            print "   Simple Search Index:\n    error(s) in node with id:"
            for item in errorindexfull:
                print "    -", item
                
        if len(errorindexext)>0:
            print "   Extended Search Index:\n    error(s) in node with id:"
            for item in errorindexext:
                print "    -", item
                
id = DbIndexer()
id.runIndexer()
#id.dropIndex()

