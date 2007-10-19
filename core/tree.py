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

from utils.utils import compare_utf8,get_filesize
from core.db import database
import logging
import sys
import os
from utils.dicts import MaxSizeDict
import core.config as config
import thread
import traceback

nodeclasses = {}
nodefunctions = {}

_root = None
conn = None
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
        if self.nr >= 1:
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
    id = conn.getRootID()
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

class NodeType:

    def __init__(self, name):
        self.name = name
        if name.find("/")>0:
            self.type = name[:name.index("/")]
            self.metadatatypename = name[name.index("/")+1:]
        else:
            self.type = name
            self.metadatatypename = name

    def getMetaFields(self,type=None):
        try:
            return self.metaFields()
        except:
            pass

        try:
            if self.metadatatypename:
                return schema.getMetaType(self.metadatatypename).getMetaFields(type)
            else:
                return []
        except AttributeError:
            return []
    
    def getMetaField(self, name):
        if self.metadatatypename:
            try:
                metadatatype = schema.getMetaType(self.metadatatypename)
                return schema.getMetaType(self.metadatatypename).getMetaField(name)
            except AttributeError:
                return None
        else:
            return None

    def getSearchFields(self):
        sfields = []
        fields = self.getMetaFields()
        fields.sort(lambda x, y: cmp(x.getOrderPos(),y.getOrderPos()))
        for field in fields:
            if field.Searchfield():
                sfields += [field]
        return sfields
    
    def getSortFields(self):
        sfields = []
        fields = self.getMetaFields()
        fields.sort(lambda x, y: cmp(x.getOrderPos(),y.getOrderPos()))
        for field in fields:
            if field.Sortfield():
                sfields += [field]
        return sfields

    def getMasks(self):
        try:
            if self.metadatatypename:
                return schema.getMetaType(self.metadatatypename).getMasks()
            else:
                return []
        except AttributeError:
            return []


    def getMask(self, name):
        try:
            if self.metadatatypename:
                return schema.getMetaType(self.metadatatypename).getMask(name)
            else:
                return []
        except AttributeError:
            return []

    def getName(self):
        return self.name

    """ get the node type (as string) """
    def getTypeName(self):
        return self.type

    def getDescription(self):
        if self.metadatatypename:
            mtype = schema.getMetaType(self.metadatatypename)
            if mtype:
                return mtype.getDescription()
            else:
                return ""

    def __getattr__(self, name):
        global nodeclasses
        cls = self.__class__
        if name in cls.__dict__:
            return cls.__dict__[name]
        elif name in self.__dict__:
            return self.__dict__[name]
        else:
            if self.type in nodeclasses:
                cls = nodeclasses[self.type]
                def r(cls):
                    if name in cls.__dict__:
                        return lambda *x,**y: cls.__dict__[name](self, *x,**y)
                    else:
                        for base in cls.__bases__:
                            ret = r(base)
                            if ret:
                                return ret
                        return None
                ret = r(nodeclasses[self.type])
                if ret:
                    return ret
                raise AttributeError("NodeType of type '"+str(self.type)+"' has no attribute '"+name+"'")
            else:
                raise AttributeError("NodeType of type '"+str(self.type)+"' has no attribute '"+name+"' (type not overloaded)")

nodetypes = {}

def getType(name):
    if name in nodetypes:
        return nodetypes[name]
    else:
        nodetypes[name] = NodeType(name)
        return nodetypes[name]

sortorders = {}

def createSortOrder(field):
    log.info("retrieving sort order for field "+field)
    reverse=0
    if field[0]=='-':
        field = field[1:]
        reverse=1

    idlist = list(conn.getSortOrder(field))

    if reverse:
        def mycmp(n1,n2):
            return compare_utf8(n2[1],n1[1])
    else:
        def mycmp(n1,n2):
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
            if type(field) == type(""):
                field = [field]
            sortlists = []
            for f in field:
                if f not in sortorders:
                    sortorders[f] = createSortOrder(f)
                sortlists.append(sortorders[f])

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
            dbnode = conn.getNode(dbid)
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

    def _makePersistent(self):
        if self.id is None:
            tree_lock.acquire()
            try:
                self.id = conn.createNode(self.name,self.type)
                if not nocache:
                    nodes_cache[long(self.id)] = self
                for name,value in self.attributes.items():
                    conn.setAttribute(self.id, name, value, check=(not bulk))
                if self.read_access:
                    conn.setNodeReadAccess(self.id,self.read_access)
                if self.write_access:
                    conn.setNodeWriteAccess(self.id,self.write_access)
                if self.data_access:
                    conn.setNodeDataAccess(self.id,self.data_access)
            finally:
                tree_lock.release()


    """ get the node name """
    def getName(self):
        return self.name


    """ set the node name """
    def setName(self,name):  
        self.name = name
        if self.id:
            conn.setNodeName(self.id,name)

    """ get the position of this node """
    def getOrderPos(self):
        return self.orderpos

    """ set the position that this node appears in nodelists """
    def setOrderPos(self,orderpos):  
        self._makePersistent()
        self.orderpos = orderpos
        conn.setNodeOrderPos(self.id,orderpos)

    """ get the node type """
    def getType(self):
        return getType(self.type)

    def getTypeName(self):
        return self.type

    """ set the node type (as string) """
    def setTypeName(self,type):
        self.type = type
        if self.id:
            conn.setNodeType(self.id,type)
            self._flushOccurences()


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
                    conn.setNodeReadAccess(self.id,access)
            elif type == "write":
                self.write_access = access
                if self.id:
                    conn.setNodeWriteAccess(self.id,access)
            elif type == "data":
                self.data_access = access
                if self.id:
                    conn.setNodeDataAccess(self.id,access)
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

        conn.addChild(self.id,child.id,check=(not bulk))
        self._flushOccurences()
        return child


    """ remove (unlink) a given child node """
    def removeChild(self,child):
        self._makePersistent()
        child._makePersistent()
        self._flush()
        child._flush()
        conn.removeChild(self.id,child.id)
        self._flushOccurences()


    """ get all FileNode subnodes of this node """
    def getFiles(self):
        self._makePersistent()
        dbfiles = conn.getFiles(self.id)
        files = []
        for filename,type,mimetype in dbfiles:
            files += [FileNode(filename,type,mimetype)]
        return files
    

    """ add a FileNode to this node """
    def addFile(self, file):
        self._makePersistent()
        conn.addFile(self.id,file.path,file.type,file.mimetype)


    """ remove a FileNode from this node """
    def removeFile(self, file):
        self._makePersistent()
        conn.removeFile(self.id,file.path)


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
                    return conn.getParents(self.id)
                else:
                    return conn.getChildren(self.id)
            if self.id is None:
                return []

            if childids_cache is None or parentids_cache is None:
                # create and fill caches
                childids_cache = self._mkCache(conn.getMappings(1))
                parentids_cache = self._mkCache(conn.getMappings(-1))

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
                    idlist = cache[long(self.id)] = conn.getParents(self.id)
                else:
                    idlist = cache[long(self.id)] = conn.getChildren(self.id)
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
        id = conn.getNamedNode(self.id,name)
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
                childids_cache = self._mkCache(conn.getMappings(1))
                parentids_cache = self._mkCache(conn.getMappings(-1))
            try:
                idlist = childids_cache[long(id)]
            except KeyError:
                idlist = []
            if idlist is None:
                idlist = childids_cache[long(id)] = conn.getChildren(id)
            for id in idlist:
                self._getAllChildIDs(str(id),map,1)
            return map
        finally:
            if not locked:
                tree_lock.release()

    """ get all decendants of this node """
    def getAllChildren(self):
        return NodeList(self._getAllChildIDs().keys())

    """ get a metadate """
    def get(self, name):
        if name == "nodename":
            return self.getName()
        if self.attributes is None:
            if not self.id:
                raise "Internal Error"
            self.attributes = conn.getAttributes(self.id)
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
            conn.setAttribute(self.id, name, value,check=(not bulk))

        try: del sortorders[name]
        except: pass

    """ get all metadates (key/value) pairs """
    def items(self):
        if self.attributes is None:
            if not self.id:
                raise "Internal Error"
            self.attributes = conn.getAttributes(self.id)
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
            conn.removeAttribute(self.id, name)

    def _flushOccurences(self):
        self.occurences = None
        for p in self.getParents():
            p._flushOccurences()

    def _getAllOccurences(self):
        if self.occurences is None:
            self.occurences = {}
            if not testmode:
                for c in self.getChildren():
                    for k,v in c._getAllOccurences().items():
                        try: self.occurences[k] += v
                        except KeyError: self.occurences[k] = v
            try: self.occurences[self.type] += 1
            except KeyError: self.occurences[self.type] = 1
        return self.occurences
    
    """ get the number of descendants of all types (hashtable) """
    def getAllOccurences(self):
        return dict([(getType(o),num) for o,num in self._getAllOccurences().items()])

    """ run a search query. returns a list of nodes """
    def search(self, q):
        log.info("search: "+q)
        self._makePersistent()
        qq = searchParser.parse(q)
        qresult = qq.execute()
        nodes = subnodes(self)
        result = qresult.intersect(nodes)
        return NodeList(result.getIDs(), result.getDescription())

    def __getattr__(self, name):
        global nodefunctions
        cls = self.__class__
        if name in cls.__dict__:
            return cls.__dict__[name]
        elif name in self.__dict__:
            return self.__dict__[name]
        elif name in nodefunctions:
            return lambda *x,**y: nodefunctions[name](self, *x,**y)
        else:
            type = self.type
            if '/' in type:
                type = type[0:type.find('/')]
            if type in nodeclasses:
                cls = nodeclasses[type]
                def r(cls):
                    if name in cls.__dict__:
                        return lambda *x,**y: cls.__dict__[name](self, *x,**y)
                    else:
                        for base in cls.__bases__:
                            ret = r(base)
                            if ret:
                                return ret
                        return None
                ret = r(nodeclasses[type])
                if ret:
                    return ret
                raise AttributeError("Node of type '"+type+"' has no attribute '"+name+"'")
            else:
                raise AttributeError("Node of type '"+type+"' has no attribute '"+name+"' (type not overloaded)")

def flush():
    global childids_cache,nodes_cache,parentids_cache,_root,conn,sortorders
    tree_lock.acquire()
    try:
        childids_cache = None
        nodes_cache = MaxSizeDict(int(config.get("db.cache_size","100000")), keep_weakrefs=1)
        parentids_cache = None
        conn = database.getConnection()
        sortorders = {}
        _root = None
    finally:
        tree_lock.release()

def registerNodeClass(type, nodeclass):
    global nodeclasses
    nodeclasses[type] = nodeclass

def registerNodeFunction(nodefunction):
    global nodefunctions
    nodefunctions[nodefunction.__name__] = nodefunction

schema = None
subnodes = None
searchParser = None
def initialize(load=1):
    global conn,_root,nodes_cache,testmode
    nodes_cache = MaxSizeDict(int(config.get("db.cache_size","100000")), keep_weakrefs=1)
    testmode = config.get("host.type", "") == "testing"
    conn = database.getConnection()
    if load:
        getRoot()
    global schema, subnodes, searchParser
    import schema.schema as schema
    schema = schema
    from core.search.query import subnodes
    subnodes = subnodes
    from core.search.parser import searchParser
    searchParser = searchParser

