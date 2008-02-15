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

from utils.utils import compare_utf8,get_filesize, compare_digit, intersection
from utils.log import logException
from core.db import database
import logging
import sys
import os
from utils.dicts import MaxSizeDict
from utils.utils import get_hash
import core.config as config
import thread
import traceback

nodeclasses = {}
nodefunctions = {}

_root = None
db = None
bulk = 0
testmode = 0
nocache = 0

log = logging.getLogger("backend")

nodes_cache = None

childids_cache = None
parentids_cache = None

class WatchLock:
    def __init__(self):
        self.nr = 0
        self.lock = thread.allocate_lock()
    def release(self):
        self.nr = self.nr - 1
        self.lock.release()
    def acquire(self):
        global testmode
        if testmode and self.nr >= 1:
            try:
                raise ""
            except:
                print "************************************"
                print "** Lock acquired more than once!  **"
                for line in traceback.extract_stack():
                    print line
                print "************************************"
        self.lock.acquire()
        self.nr = self.nr + 1

tree_lock = WatchLock()

def getRootID():
    id = db.getRootID()
    return id

def getGlobalRoot():
    global _root
    if _root is not None:
        return _root
    id = getRootID()
    if id is None:
        return None
    _root = getNode(id)
    return _root

def getRoot(name=None):
    _root = getGlobalRoot()
    if name is None:
        return _root
    else:
        return _root.getChild(name)

def getNode(id):
    global nodes_cache,nocache
    try:
        long(id)
    except ValueError:
        raise NoSuchNodeError(id)
    except TypeError:
        raise NoSuchNodeError(id)

    if nocache:
        return Node(dbid=id)
    tree_lock.acquire()
    try:
        try:
            return nodes_cache[long(id)]
        except KeyError:
            pass
    finally:
        tree_lock.release()
    node = nodes_cache[long(id)] = Node(dbid=id)
    return node

class NoSuchNodeError:
    def __init__(self,id=None):
        self.id = id
    def __str__(self):
        return "NoSuchNodeError("+str(self.id)+")"

class InvalidOperationError:
    pass

class FileNode:
    def __init__(self, name, type, mimetype):
        if name.startswith(config.settings["paths.datadir"]):
            name = name[len(config.settings["paths.datadir"]):]
        self.path = name
        self.type = type
        self.mimetype = mimetype
    def getType(self):
        return self.type
    def getPath(self):
        return config.settings["paths.datadir"] + self.path
    def getMimeType(self):
        return self.mimetype
    def getSize(self):
        return get_filesize(self.getPath())
    def getHash(self):
        return get_hash(self.getPath())
    def getName(self):
        return os.path.basename(self.path)

nodetypes = {}

' TODO update for current tree implementation'
def getType(name):
    if name in nodetypes:
        return nodetypes[name]
    else:
        nodetypes[name] = name
        return nodetypes[name]

sortorders = {}

changed_metadata_nodes = {}
last_changed_metadata_node = None
def flush_changed_metadata():
  
    global searcher

    for nid in changed_metadata_nodes.keys():
        searcher.node_changed(getNode(nid))

    changed_metadata_nodes.clear()
    last_changed_metadata_node = None
    
def changed_metadata(node):
    if node.id:
        changed_metadata_nodes[node.id] = None
        last_changed_metadata_node = node.id

def createSortOrder(field):
    log.info("retrieving sort order for field "+field)
    reverse=0
    if field[0]=='-':
        field = field[1:]
        reverse=1

    idlist = list(db.getSortOrder(field))

    if reverse:
        def mycmp(n1,n2):
            if str(n1[1]).isdigit() and str(n2[1]).isdigit():
                return compare_digit(n2[1],n1[1])
            else:
                return compare_utf8(n2[1],n1[1])
    else:
        def mycmp(n1,n2):
            if str(n1[1]).isdigit() and str(n2[1]).isdigit():
                return compare_digit(n1[1],n2[1])
            else:
                return compare_utf8(n1[1],n2[1])
    idlist.sort(mycmp)

    i = 0
    v = None
    id2pos = {}
    for id,value in idlist:
        if value != v:
            v = value
            i = i + 1
        id2pos[int(id)] = i
    return id2pos

class NodeList:
    def __init__(self, ids,description=""):
        self.ids = ids
        self.len = len(ids)
        self.description = description
    def __len__(self):
        return self.len
    def __getitem__(self, i):
        if type(i) == slice:
            nodes = []
            for id in self.ids[i]:
                nodes += [getNode(str(id))]
            return nodes
        elif i >= self.len:
            raise IndexError(str(i)+" >= "+str(self.len))
        return getNode(str(self.ids[i]))
    
    def getIDs(self):
        return self.ids
        
    def getDescription(self):
        return self.description
    def sort(self,field="orderpos"):
        if field == "orderpos":
            nodes = []
            for id in self.ids:
                nodes += [getNode(str(id))]
            def orderposcmp(n1,n2):
                if n1.orderpos > n2.orderpos:
                    return 1
                elif n1.orderpos < n2.orderpos:
                    return -1
                else:
                    return 0
            nodes.sort(orderposcmp)
            return nodes
        elif field == "name":
            nodes = []
            for id in self.ids:
                nodes += [getNode(str(id))]
            def namecmp(n1,n2):
                result = compare_utf8(n1.name,n2.name)
                return result
            nodes.sort(namecmp)
            # we don't return a NodeList here, but a normal
            # list. The main difference between those two is
            # that a normal list doesn't have an "intersect" operation.
            # That's ok because we don't want to intersect sorted
            # lists.
            return nodes
        else:
            if not field:
                return self
            if type(field) == type(""):
                field = [field]
            sortlists = []
            for f in field:
                if f:
                    if f not in sortorders:
                        sortorders[f] = createSortOrder(f)
                    sortlists.append(sortorders[f])
            if not sortorders:
                return self

            def fieldcmp(id1,id2):
                for s in sortlists:
                    pos1 = s.get(int(id1),-1)
                    pos2 = s.get(int(id2),-1)
                    if pos1 < pos2:
                        return -1
                    elif pos1 > pos2:
                        return 1
                return 0
            self.ids.sort(fieldcmp)
            return self
            
    def filter(self, access):
        return access.filter(self)

class Node:
    def __init__(self, name="<unbenannt>", type=None, dbid=None):
        self.occurences = None
        if dbid is None:
            if type == None:
                raise "Node must have a type"
            self.id = None
            self.name = name
            self.type = type
            self.read_access = None
            self.write_access = None
            self.data_access = None
            self.orderpos = 1
            self.attributes = {}
            if type == "root":
                self._makePersistent()
        else:
            dbnode = db.getNode(dbid)
            if not dbnode:
                raise NoSuchNodeError(dbid)
            id,name,type,read,write,data,orderpos = dbnode

            self.id = id
            self.name = name
            self.type = type
            self.read_access = read
            self.write_access = write
            self.data_access = data
            self.orderpos = orderpos
            self.attributes = None
        self.occurences = {}
        self.occurences2node = {}

    def _makePersistent(self):
        if self.id is None:
            changed_metadata(self)
            tree_lock.acquire()
            try:
                self.id = db.createNode(self.name,self.type)
                if not nocache:
                    nodes_cache[long(self.id)] = self
                for name,value in self.attributes.items():
                    db.setAttribute(self.id, name, value, check=(not bulk))
                if self.read_access:
                    db.setNodeReadAccess(self.id,self.read_access)
                if self.write_access:
                    db.setNodeWriteAccess(self.id,self.write_access)
                if self.data_access:
                    db.setNodeDataAccess(self.id,self.data_access)
            finally:
                tree_lock.release()


    """ get the node name """
    def getName(self):
        return self.name


    """ set the node name """
    def setName(self,name):  
        self.name = name
        if self.id:
            db.setNodeName(self.id,name)

    """ get the position of this node """
    def getOrderPos(self):
        return self.orderpos

    """ set the position that this node appears in nodelists """
    def setOrderPos(self,orderpos):  
        self._makePersistent()
        self.orderpos = orderpos
        db.setNodeOrderPos(self.id,orderpos)

    """ get the node type """
    def getType(self):
        return self

    """ get the node object/document type """
    def getContentType(self):
        if '/' in self.type:
            return self.type[0:self.type.find('/')]
        else:
            return self.type

    """ get the node schema """
    def getSchema(self):
        if '/' in self.type:
            return self.type[self.type.find('/')+1:]
        else:
            return self.type
           
    """ set the node type (as string) """
    def setTypeName(self,type):
        changed_metadata(self)
        self.type = type
        if self.id:
            db.setNodeType(self.id,type)
            self._flushOccurences()

    def setSchema(self,schema):
        doctype = self.getContentType()
        self.setTypeName(doctype+"/"+schema)

    def setContentType(self,doctype):
        schema = self.getSchema()
        self.setTypeName(doctype+"/"+schema)

    """ get a named access right (e.g. read, write, etc.)"""
    def getAccess(self, type):
        if type == "read":
            return self.read_access
        elif type == "write":
            return self.write_access
        elif type == "data":
            return self.data_access

    """ set a named access right (e.g. read, write, etc.)"""
    def setAccess(self, type, access):
        tree_lock.acquire()
        try:
            if type == "read":
                self.read_access = access
                if self.id:
                    db.setNodeReadAccess(self.id,access)
            elif type == "write":
                self.write_access = access
                if self.id:
                    db.setNodeWriteAccess(self.id,access)
            elif type == "data":
                self.data_access = access
                if self.id:
                    db.setNodeDataAccess(self.id,access)
        finally:
            tree_lock.release()


    def _flush(self):
        global childids_cache,parentids_cache
        childs = self._getChildIDs()
        parents = self._getChildIDs(1)
        tree_lock.acquire()
        try:
            for id in childs + parents + [long(self.id)]:
                childids_cache[id] = None
                parentids_cache[id] = None
        finally:
            tree_lock.release()
    
    """ add a child node """
    def addChild(self,child):
        self._makePersistent()
        child._makePersistent()
        self._flush()
        child._flush()

        if self.id == child.id or self.id in child._getAllChildIDs():
            raise InvalidOperationError()

        db.addChild(self.id,child.id,check=(not bulk))
        self._flushOccurences()
        return child


    """ remove (unlink) a given child node """
    def removeChild(self,child):
        self._makePersistent()
        child._makePersistent()
        self._flush()
        child._flush()
        db.removeChild(self.id,child.id)
        self._flushOccurences()


    """ get all FileNode subnodes of this node """
    def getFiles(self):
        self._makePersistent()
        dbfiles = db.getFiles(self.id)
        files = []
        for filename,type,mimetype in dbfiles:
            files += [FileNode(filename,type,mimetype)]
        return files
    

    """ add a FileNode to this node """
    def addFile(self, file):
        changed_metadata(self)
        self._makePersistent()
        db.addFile(self.id,file.path,file.type,file.mimetype)


    """ remove a FileNode from this node """
    def removeFile(self, file):
        changed_metadata(self)
        self._makePersistent()
        db.removeFile(self.id,file.path)


    def _mkCache(self, source):
        cache = {}
        lastid = None
        list = []
        for id,childid in source:
            if id != lastid:
                if lastid is not None:
                    cache[long(lastid)] = list
                list = []
                lastid = id
            list += [long(childid)]
        if lastid is not None:
            cache[long(lastid)] = list
        return cache


    def _getChildIDs(self, parents=0):
        global childids_cache,parentids_cache
        tree_lock.acquire()
        try:
            if nocache:
                if parents:
                    return db.getParents(self.id)
                else:
                    return db.getChildren(self.id)
            if self.id is None:
                return []

            if childids_cache is None or parentids_cache is None:
                # create and fill caches
                childids_cache = self._mkCache(db.getMappings(1))
                parentids_cache = self._mkCache(db.getMappings(-1))

            if parents:
                cache = parentids_cache
            else:
                cache = childids_cache
            try: 
                idlist = cache[long(self.id)]
            except KeyError:
                return []
            if idlist is None:
                if parents:
                    idlist = cache[long(self.id)] = db.getParents(self.id)
                else:
                    idlist = cache[long(self.id)] = db.getChildren(self.id)
            return idlist
        finally:
            tree_lock.release()

    """ get all direct children of this node """
    def getChildren(self):
        idlist = self._getChildIDs(0)
        return NodeList(idlist)

    """ get a child with a specific node name """
    def getChild(self, name):
        if name is None:
            raise NoSuchNodeError("child:None")
        if not self.id:
            raise NoSuchNodeError("child of None")
        id = db.getNamedNode(self.id,name)
        if not id:
            print "subnode of ",self.id,self.name," with name '" + str(name) + "' not found"
            raise NoSuchNodeError("child:"+str(name))
        return getNode(str(id))

    """ get all parents of this node """
    def getParents(self):
        idlist = self._getChildIDs(1)
        return NodeList(idlist)

    """ get the number of direct children of this node """
    def getNumChildren(self):
        idlist = self._getChildIDs()
        return len(idlist)


    def _getAllChildIDs(self, id=None, map=None, locked=0):
        global childids_cache,parentids_cache
        if not locked:
            tree_lock.acquire()
        try:
            if map is None:
                map = {}
            if id is None:
                id = self.id
            if id is None:
                return {}
            map[id] = None
            if childids_cache is None or parentids_cache is None:
                # create and fill caches
                childids_cache = self._mkCache(db.getMappings(1))
                parentids_cache = self._mkCache(db.getMappings(-1))
            try:
                idlist = childids_cache[long(id)]
            except KeyError:
                idlist = []
            if idlist is None:
                idlist = childids_cache[long(id)] = db.getChildren(id)
            for id in idlist:
                self._getAllChildIDs(str(id),map,1)
            return map
        finally:
            if not locked:
                tree_lock.release()

    """ get all decendants of this node """
    def getAllChildren(self):
        return NodeList(self._getAllChildIDs().keys())

        
    def event_metadata_changed(self):
        global searcher
        searcher.node_changed(self)
        
    
    """ get a metadate """
    def get(self, name):
        if name == "nodename":
            return self.getName()
        if self.attributes is None:
            if not self.id:
                raise "Internal Error"
            self.attributes = db.getAttributes(self.id)
        return self.attributes.get(name, "")

    """ set a metadate """
    def set(self, name, value):
        if name == "nodename":
            return self.setName(value)
        if self.attributes is None:
            if not self.id:
                raise "Internal Error"
        else:
            self.attributes[name] = value

        if self.id:
            db.setAttribute(self.id, name, value,check=(not bulk))

        try: del sortorders[name]
        except: pass

    """ get all metadates (key/value) pairs """
    def items(self):
        if self.attributes is None:
            if not self.id:
                raise "Internal Error"
            self.attributes = db.getAttributes(self.id)
        return self.attributes.items()


    def setAttribute(self, name, value):
        self.set(name,value)
    def getAttribute(self, name):
        return self.get(name)

    def removeAttribute(self, name):
        if self.attributes:
            try: del self.attributes[name]
            except KeyError: pass
        if self.id:
            db.removeAttribute(self.id, name)

    def _flushOccurences(self):
        self.occurences = {}
        self.occurences2node = {}
        for p in self.getParents():
            p._flushOccurences()

    def getAllOccurences(self, access):
        level = access.getPrivilegeLevel()
        if level not in self.occurences:
            self.occurences[level] = {}
            self.occurences2node[level] = {}
            nodelist = access.filter(self.getAllChildren())
            for node in nodelist:
                schema = node.getSchema()
                if schema not in self.occurences[level]:
                    self.occurences[level][schema] = 1
                    self.occurences2node[level][schema] = node
                else:
                    self.occurences[level][schema] += 1
        return dict([(self.occurences2node[level][s],v) for s,v in self.occurences[level].items()])
    
    """ run a search query. returns a list of nodes """
    def search(self, q):
        global searcher, subnodes
        log.info('search: '+q+' for node '+str(self.id))
        self._makePersistent()
        items = subnodes(self)
        
        if type(items)!= list:
            items = items.getIDs()
        q = q.replace("\"","'")
        return intersection([items, searcher.query(q)])


    def __getattr__(self, name):
        global nodefunctions,nodeclasses
        cls = self.__class__
        if name in cls.__dict__:
            return cls.__dict__[name]
        if name in self.__dict__:
            return self.__dict__[name]
        if self.getContentType() in nodeclasses:
            cls = nodeclasses[self.getContentType()]
            def r(cls):
                if name in cls.__dict__:
                    return lambda *x,**y: cls.__dict__[name](self, *x,**y)
                else:
                    for base in cls.__bases__:
                        ret = r(base)
                        if ret:
                            return ret
                    return None
            ret = r(nodeclasses[self.getContentType()])
            if ret:
                return ret
        if name in nodefunctions:
            return lambda *x,**y: nodefunctions[name](self, *x,**y)
        if self.getContentType() in nodeclasses:
            raise AttributeError("Node of type '"+self.type+"' has no attribute '"+name+"'")
        else:
            raise AttributeError("Node of type '"+self.type+"' has no attribute '"+name+"' (type not overloaded)")

    
    # fill hashmap with idlists of listvalues
    def getAllAttributeValues(self, attribute, access):
        if not hasattr(self, 'attrlist') or attribute not in self.attrlist.keys():
            self.attrlist = {}
            self.attrlist[attribute] = {}
            
            # current attribute not listed -> create id list
            if not "all" in self.attrlist[attribute].keys():
                self.attrlist[attribute]["all"] = {}            
                ret = {}
                for node in self.getAllChildren():
                    v = node.get(attribute)
                    if v not in ret.keys():
                        ret[v] =[]
                    ret[v].append(node.id)

                for key in ret.keys():
                    self.attrlist[attribute]["all"][key] = NodeList(ret[key], key)

        if not str(access.getPrivilegeLevel()) in self.attrlist[attribute].keys():
            self.attrlist[attribute][str(access.getPrivilegeLevel())] = {}
            for item in self.attrlist[attribute]["all"].keys():
                self.attrlist[attribute][str(access.getPrivilegeLevel())][item] = len(self.attrlist[attribute]["all"][item].filter(access))
        return self.attrlist[attribute][str(access.getPrivilegeLevel())]

            
def flush():
    global childids_cache,nodes_cache,parentids_cache,_root,db,sortorders
    tree_lock.acquire()
    try:
        childids_cache = None
        nodes_cache = MaxSizeDict(int(config.get("db.cache_size","100000")), keep_weakrefs=1)
        parentids_cache = None
        db = database.getConnection()
        sortorders = {}
        _root = None
    finally:
        tree_lock.release()

def registerNodeClass(type, nodeclass):
    global nodeclasses
    nodeclasses[type] = nodeclass

def registerNodeFunction(name, nodefunction):
    global nodefunctions
    nodefunctions[name] = nodefunction

schema = None
subnodes = None
searchParser = None
searcher = None

def initialize(load=1):
    global db,_root,nodes_cache,testmode
    nodes_cache = MaxSizeDict(int(config.get("db.cache_size","100000")), keep_weakrefs=1)
    testmode = config.get("host.type", "") == "testing"
    db = database.getConnection()
    if load:
        getRoot()
    global schema, subnodes, searchParser, searcher
    import schema.schema as schema
    schema = schema

    if config.get("config.searcher","")=="fts3": # use fts3
        print "fts3 searcher initialized"
        from core.search.ftsquery import subnodes, ftsSearcher
        from core.search.ftsparser import ftsSearchParser
        
        subnodes = subnodes
        searchParser = ftsSearchParser
        searcher = ftsSearcher
        
    else: # use magpy
        print "magpy searcher initialized"
        from core.search.query import subnodes, mgSearcher
        from core.search.parser import searchParser
        
        subnodes = subnodes
        searchParser = searchParser
        searcher = mgSearcher
    
    

