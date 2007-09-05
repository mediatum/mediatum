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
import core.tree as tree
import core.config as config
import mgquery
import os
import core.db.database as database
import time
import sys
import schema.schema as schema
import logging
import thread
import traceback
import date
from utils import *

log = logging.getLogger("backend")
search_lock = thread.allocate_lock()

class QueryResult(tree.NodeList):
    def __init__(self, searcher, ids=None, words=""):
        self.searcher = searcher
        if ids is not None:
            self.ids = ids
        else:
            self.ids = None
        self.words = words.strip()
    
    def getIDs(self):
        result = {}
        if self.searcher.s2n:
            for id in self.ids:
                try:
                    result[self.searcher.s2n[id]] = None
                except IndexError:
                    pass
        return result.keys()

    def size(self):
        if self.ids is None:
            return 0
        return len(self.ids)

    def __len__(self):
        return self.size()

    def _joinDesc(self,s1,s2):
        if s1:
            if s2:
                return s1+" "+s2
            else:
                return s1
        else:
            if s2:
                return s1+" "+s2
            else:
                return s2

    def merge(self, other):
        if self.searcher is None:
            self.searcher = other.searcher
        if self.ids is None:
            return QueryResult(self.searcher, other.ids, self._joinDesc(other.words,self.words))
        if other.ids is None:
            return QueryResult(self.searcher, self.ids, self._joinDesc(other.words,self.words))
        ids = self.ids.intersection(other.ids)
        print "Merging returns",len(ids),"results"
        return QueryResult(self.searcher, ids, self._joinDesc(other.words,self.words))

    def intersect(self, other):
        return self.merge(other)

    def getDescription(self):
        return self.words

collections = {}

class _Searcher:

    def __init__(self, name):
        self.tmpdir = config.settings["paths.searchstore"]
        self.name = name
       
        try:
            self.searcher = mgquery.MGSearchStore(config.settings["paths.searchstore"], self.name)
        except:
            log.info(formatException())
            self.searcher = None
            self.s2n = None
            return

        self.searchindex2node = [None]
        collection="root"
        if collection in collections:
            self.s2n = collections[collection]
        else:
            fi = open(self.tmpdir + "s2n.txt", "rb")
            self.s2n = []
            while 1:
                s = fi.readline()
                if not s:
                    break
                self.s2n += [s.strip()]
            fi.close()
            collections[collection] = self.s2n

    def index(self):
        if not self.searcher:
            return []
        return self.searcher.getIndex()

    def search(self,q):
        
        if not self.searcher:
            return QueryResult(self)

        try:
            q = unicode(q, "utf-8").encode("latin-1")
        except:
            pass

        query = self.searcher.newQuery(q)
        intset = query.intset()
        
        words2 = []
        for word in query.words():
            try:
                words2 += [unicode(word,"latin-1").encode("utf-8")]
            except:
                words2 += [word]

        return QueryResult(self, intset, ArrayToString(words2, " "))


searchers = {}

def _getSearcher(name):
    global searchers
    tmpdir = config.settings["paths.searchstore"]
    try:
        search_lock.acquire()
        try:
            s = searchers[name]
        except:
            searchers[name] = s = _Searcher(name)
    finally:
        search_lock.release()
    return s

def query(field, value):
    searcher = _getSearcher(field) 
    r = searcher.search(value)
    print "Looking for",field,"with value",value,":",len(r),"results"
    return r

def numquery(field, fromVal, toVal):
    searcher = _getSearcher(field) 
    r = searcher.search(str(fromVal)+"-"+str(toVal))
    print "Looking for",field,"with value between",fromVal,"and",toVal,":",len(r),"results"
    return r

def subnodes(node):
    searcher = _getSearcher("mindex")
    r = searcher.search(node.get("lindex")+"-"+node.get("rindex"))
    print "Retrieving subnodes of",node.id,node.name,":",len(r),"results"
    return r

def getGlobalIndex(type):
    values = {}
    fields = database.getConnection().getMetaFields(type)
    for f in fields:
        for s in f[0].split(";"):
            values[s.strip()] = None
    return values.keys()

def flush():
    global searchers,collections
    searchers = {}
    collections = {}

def _getNodeList(node):
    nodelist = {}
    def recurse(node, nodelist):
        nodelist[node.id] = node
        for c in node.getChildren():
            recurse(c, nodelist)

    recurse(node, nodelist)
    return nodelist.values()

def UTF8ToLatin(v):
    try:
        v = unicode(v,"utf-8").encode("latin-1",'replace')
    except UnicodeDecodeError:
        pass # happens all the time, unfortunately
    return v

def _makeMetadataNumbers():
    print "Making Metadatafield-Index"
    m = schema.loadTypesFromDB()
    for metatype in m:
        for field in metatype.getMetaFields():
            if field.getFieldtype() in ["list","mlist"] and field.Searchfield():
                #print metatype.getName(),"->",field.getName()
                nstr = ""
                for v in field.getValueList():
                    v = UTF8ToLatin(v)
                    num = 0
                    for collection in tree.getRoot("collections").getChildren():
                        if collection.type == "collection":
                            try:
                                query = "%s=%s and schema=%s" % (field.getName(), v, metatype.getName())
                                n = len(collection.search(query))
                            except:
                                n= 0
                            num += n
                            #print "\t", collection.name, field.getName(), v,"->",n
                    if len(nstr):
                        nstr+=";"
                    nstr += str(num)
                field.setFieldValueNum(nstr)

def _makeTreeIndices():
    print "Analyzing tree structure"

    id2mindex = {}

    def r(node,pos):
        pos[0] += 1

        try:
            id2mindex[node.id] += ";"+str(pos[0])
        except KeyError:
            id2mindex[node.id] = str(pos[0])

        node.set("mindex", id2mindex[node.id])

        node.set("lindex", str(pos[0]))
        for c in node.getChildren():
            r(c,pos)
        node.set("rindex", str(pos[0]))

    r(tree.getRoot(),[0])

def _makeCollectionIndices():
    tmpdir = config.settings["paths.searchstore"]

    _makeTreeIndices()

    print "Retrieving node list..."
    
    nodelist = _getNodeList(tree.getRoot())
    print len(nodelist),"nodes"

    fi = open(tmpdir + "s2n.txt", "wb")
    fi.write("--START--\n")
    for node in nodelist:
        fi.write(node.id + "\n")
    fi.close()

    def mkIndex(name, field, type, data=None):
        print "Making Index",name
        file = tmpdir+name+".searchfile.txt"
        fi = open(file, "wb")

        for node in nodelist:
            if field == "alltext":
                s = ""
                if node.type != "directory":
                    for key,val in node.items():
                        if val:
                            s += val+"\n"
                    s += node.getName()

                #for nfile in node.getFiles():
                #    if nfile.type == "fulltext":
                #        try:
                #            fi2 = open(nfile.getPath(), "rb")
                #            s += " "
                #            s += fi2.read()
                #            s += " "
                #            fi2.close()
                #        except IOError:
                #            log.error("Couldn't access file "+nfile.getPath())
            elif field == "fulltext":
                s = ""
                if node.type != "directory":
                    for nfile in node.getFiles():
                        if nfile.type == "fulltext":
                            try:
                                fi2 = open(nfile.getPath(), "rb")
                                s += " "
                                s += fi2.read()
                                s += " "
                                fi2.close()
                            except IOError:
                                log.error("Couldn't access file "+nfile.getPath())

                #c1 = "abcdefghijklmnop"[(int(node.id)>>28)&15]
                #c2 = "abcdefghijklmnop"[(int(node.id)>>24)&15]
                #c3 = "abcdefghijklmnop"[(int(node.id)>>20)&15]
                #c4 = "abcdefghijklmnop"[(int(node.id)>>16)&15]
                #c5 = "abcdefghijklmnop"[(int(node.id)>>12)&15]
                #c6 = "abcdefghijklmnop"[(int(node.id)>>8)&15]
                #c7 = "abcdefghijklmnop"[(int(node.id)>>4)&15]
                #c8 = "abcdefghijklmnop"[(int(node.id)>>0)&15]
                #s += " mx" + c8+c7+c6+c5+c4+c3+c2+c1 + " "
            elif field == "everything":
                s = ""
                if node.type != "directory":
                    for key,val in node.items():
                        if val:
                            s += UTF8ToLatin(val)+"\n"
                    s += UTF8ToLatin(node.getName())
                    for nfile in node.getFiles():
                        if nfile.type == "fulltext":
                            try:
                                fi2 = open(nfile.getPath(), "rb")
                                s += " "
                                s += fi2.read()
                                s += " "
                                fi2.close()
                            except IOError:
                                log.error("Couldn't access file "+nfile.getPath())

            elif field == "objtype":
                s = node.type
                if "/" in s:
                    s = s[:s.index("/")]
            elif field == "schema":
                s = node.type
                if "/" in s:
                    s = s[s.index("/")+1:]
                else:
                    s = ""
            elif type == "union":
                s = ""
                for item in data:
                    field = node.get(item)
                    if field:
                        s += field + " "
            else:
                s = node.get(field)
                if type=="date":
                    if len(s):
                        try:
                            s = str(date.parse_date(s).daynum())
                        except:
                            print "Couldn't parse date",s
                            s = "0"

            s = UTF8ToLatin(s)
            fi.write(s.replace("\2"," ") + "\n")
            fi.write("\2")

        if type != "num" and type != "date":
            fi.write("ecjfadf;jwkljer;jfklajd;gyugi;wyuogsdfjg;wuriosygh;nmwert;bwweriwoue;jfkajsdf;nmweurwu;hkethre;ghbyxuidfg;ewrioafi;ewirjglsag;vhxyseoru;vnmwerwe;fajsdfwetrh")
        fi.close()

        basename = name

        itype = "makeindex"
        if type=="date" or type=="num":
            itype = "makeNumIndex"
        elif type=="list" or type=="mlist" or type=="ilist":
            itype = "makeClassIndex"

        command = "%s %s %s %s %s %s" % (sys.executable, os.path.join(config.basedir,"search/runindexer.py"),itype,file,tmpdir,basename)
        exit_status = os.system(command)
        if exit_status:
            print "Exit status "+str(exit_status)+" of subprocess "+command
            sys.exit(1)
            #raise "Exit status "+str(exit_status)+" of subprocess "+command
        #mgindexer.makeindex(file, tmpdir, name) 

    occurs = tree.getRoot().getAllOccurences()
    searchfields = []
    for mtype,num in occurs.items():
        if num>0:
            fields = mtype.getMetaFields()
            for field in fields:
                if field.Searchfield():
                    searchfields += [field]

    mkIndex("full","alltext","text")
    mkIndex("everything","everything","text")
    mkIndex("objtype","objtype","list")
    mkIndex("schema","schema","list")
    mkIndex("mindex","mindex","num")
    mkIndex("updatetime","updatetime","date")
    for f in searchfields:
        mkIndex(f.getName(), f.getName(), f.getFieldtype(), f.getValueList())


def makeSearchIndex():
    search_lock.acquire()
    try:
        _makeCollectionIndices()
        flush()
    finally:
        search_lock.release()
    _makeMetadataNumbers()

def indexer_thread(timewait):
    if timewait<10:
        timewait = 10
    while 1:
        time.sleep(timewait-10)
        log.info("Re-indexing Database")
        time.sleep(10)
        makeSearchIndex()
        log.info("Re-indexing Database: done")
        tree.getRoot().set("lastindexerrun",date.format_date())

def startThread():
    timewait = config.get("config.reindex_time")
    if timewait:
        thread_id = thread.start_new_thread(indexer_thread, (int(timewait),))
        log.info("started indexer thread. frequency "+str(timewait)+", thread id " + str(thread_id))
    else:
        log.info("no indexer thread started. Indexes will need to be updated manually")

