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

from utils.utils import compare_utf8,get_filesize, compare_digit, intersection, u, iso2utf8, float_from_gps_format
from utils.log import logException
from core.db import database
import logging
import time
import sys
import os
from utils.dicts import MaxSizeDict
from utils.utils import get_hash
import core.config as config
import thread
import traceback

nodeclasses = {}
nodefunctions = {}
contentstyles = {}
filehandlers = []

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
    def __init__(self, mode=0):
        self.mode = mode
        self.nr = 0
        self.lock = thread.allocate_lock()
    def release(self):
        self.nr = self.nr - 1
        self.lock.release()
    def acquire(self):
        if self.mode and self.nr >= 1:
            try:
                raise ""
            except:
                print "** Lock acquired more than once!  **"
                for line in traceback.extract_stack():
                    print line
                print "************************************"
        self.lock.acquire()
        self.nr = self.nr + 1

tree_lock = WatchLock(testmode)

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
    
def getAllContainerChildrenNum(node, count=0): # returns the number of children
    for n in node.getContainerChildren():
        count = getAllContainerChildrenNum(n, count)
    count += len(node.getContentChildren())
    return count

    
def getAllContainerChildrenAbs(node, count=[]): # returns a list with children, each child once
    for n in node.getContainerChildren():
        count = getAllContainerChildrenAbs(n, count)
    count.extend(node.getContentChildren().ids)
    return count

def getAllContainerChildren(node):
    return len(list(set(getAllContainerChildrenAbs(node, [])))) # get number of children
    #return getAllContainerChildrenNum(node, 0) # get number of children (faster)
    #return 0 # suppress number (fastest)

    
def getNodesByAttribute(attributename, attributevalue=""):
    return db.getNodeIdByAttribute(attributename, attributevalue)

def getDirtyNodes(num=0):
    return NodeList(db.getDirty(num))
    

class NoSuchNodeError:
    def __init__(self,id=None):
        self.id = id
    def __str__(self):
        return "NoSuchNodeError("+str(self.id)+")"

class InvalidOperationError:
    pass

class FileNode:
    def __init__(self, name, type, mimetype, node=None):
        if name.startswith(config.settings["paths.datadir"]):
            name = name[len(config.settings["paths.datadir"]):]
        self._path = name
        #self.path = name # workaround, until CVS is updated everywhere
        self.type = type
        self.mimetype = mimetype
        self.node = node
        
    def clone(self, node):
        """Creates a deep copy of this filenode, i.e. there is a new version of the file on the drive being created!"""
        from utils.fileutils import importFileRandom
        f = importFileRandom(self.retrieveFile())
        f.node = node
        f.type = self.type
        f.mimetype = self.mimetype
        return f

    def getType(self):
        return self.type
    def _add(self):
        for f in filehandlers:
            if hasattr(f, "add"):
              try:
                  if f.add(self):
                      return
              except: 
                  logException("file handler add() failed")
    def _delete(self):
        for f in filehandlers:
            if hasattr(f, "delete"):
              try:
                  if f.delete(self):
                      return
              except: 
                  logException("file handler delete() failed")
    
    def retrieveFile(self):
        for f in filehandlers:
            if hasattr(f, "retrieveFile"):
                try:
                    path = f.retrieveFile(self)
                    if path:
                        return path
                except: 
                    logException("file handler retrieveFile() failed")
        
        if os.path.exists(self._path):
            return self._path

        if os.path.exists(config.basedir+"/" + self._path):
            return config.basedir+"/" + self._path

        if not os.path.exists(config.settings["paths.datadir"] + self._path):
            for f in self.node.getFiles():
                if f.getType().startswith("presentati"):
                    try:
                        #_n = os.path.dirname(f.retrieveFile())+"/"+self._path
                        _n = os.path.dirname(f._path)+"/"+self._path
                        if os.path.exists(_n):
                            return _n
                    except:
                        pass
        return config.settings["paths.datadir"] + self._path
        
    def getMimeType(self):
        return self.mimetype
    def getSize(self):
        for f in filehandlers:
            if hasattr(f, "getSize"):
                try:
                    size = f.getSize(self)
                    if size:
                        return size
                    else:
                        return 0
                except: 
                    logException("file handler getSize() failed")
                    return -1
        return get_filesize(self.retrieveFile())
    def getHash(self):
        for f in filehandlers:
            if hasattr(f, "getHash"):
                try:
                    h = f.getHash(self)
                    if h:
                        return h
                except: 
                    logException("file handler getHash() failed")
        return get_hash(self.retrieveFile())
    def getName(self):
        return os.path.basename(self._path)
        
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
    log.info("retrieving sort order for field '"+field+"'")
    t1 = time.time()
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
    msg = "sort order retrieved for field '"+field+"': "+str(time.time()-t1)+" seconds  -  "
    msg += "id2pos has %d keys" % len(id2pos)
    log.info(msg)
    return id2pos

class NodeList:
    def __init__(self, ids, description=""):
        if isinstance(ids, NodeList):
            ids = ids.ids
        elif len(ids) and isinstance(ids[0], Node):
            nodes = ids
            ids = [None]*len(nodes)
            for i,n in enumerate(nodes):
                ids[i]=n.id
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
    def sort(self,field="orderpos", direction="up"):
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
                if direction=="up":
                    nodes.sort(namecmp)
                
                def namecmp_down(n1,n2):
                    result = compare_utf8(n2.name,n1.name)
                    return result
                if direction=="down":
                    nodes.sort(namecmp_down)
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
        self.lock = thread.allocate_lock() # for attrlist
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
            self.localread = None
            if type == "root":
                self._makePersistent()
        else:
            dbnode = db.getNode(dbid)
            if not dbnode:
                raise NoSuchNodeError(dbid)
            id,name,type,read,write,data,orderpos,localread = dbnode

            self.id = id
            self.name = name
            self.type = type
            self.read_access = read
            self.write_access = write
            self.data_access = data
            self.orderpos = orderpos
            self.attributes = None
            self.localread = localread

            self.getLocalRead()
        self.occurences = {}
        self.occurences2node = {}
        self.ccount = -1
        if hasattr(self, 'overload'):
            self.overload()

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

    def setDirty(self):
        db.setDirty(self.id)
        
    def isDirty(self):
        if db.isDirty(self.id):
            return 1
        else:
            return 0
    
    def cleanDirty(self):
        db.cleanDirty(self.id)

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

    def invalidateLocalRead(self):
        self.localread = ""
        if self.id:
            db.setNodeLocalRead(self.id, self.localread)
        for c in self.getChildren():
            c.invalidateLocalRead()

    def getLocalRead(self):
        if not self.localread:            
            if self.id is None:
                return self.read_access

            def p(node,rights):
                r = node.read_access
                if r:
                    for rule in r.split(","):
                        rights[rule]=None
                else:
                    for c in node.getParents():
                        p(c,rights)
            rights = {}
            p(self,rights)
            self.localread = ",".join(rights.keys())
            db.setNodeLocalRead(self.id, self.localread)
        return self.localread
        
    def resetLocalRead(self):
        self.localread = ""
        db.setNodeLocalRead(self.id, self.localread)
           
    """ set the node type (as string) """
    def setTypeName(self,type):
        changed_metadata(self)
        self.type = type
        if self.id:
            db.setNodeType(self.id,type)
            self._flushOccurences()

    def setSchema(self,schema):
        doctype = self.getContentType()
        if schema:
            self.setTypeName(doctype+"/"+schema)
        else:
            self.setTypeName(doctype)

    def setContentType(self,doctype):
        if "/" in self.type:
            schema = self.getSchema()
            self.setTypeName(doctype+"/"+schema)
        else:
            self.setTypeName(doctype)

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
        if self.id and type=="read":
            self.invalidateLocalRead()


    def _flush(self):
        global childids_cache,parentids_cache
        childs = self._getChildIDs()
        parents = self._getChildIDs(1)
        self.ccount = -1
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
        child.resetLocalRead()
        for c in child.getAllChildren():
            c.resetLocalRead()
        return child


    """ remove (unlink) a given child node """
    def removeChild(self, child):
        self._makePersistent()
        child._makePersistent()
        self._flush()
        child._flush()
        db.removeChild(self.id,child.id)
        child.resetLocalRead()
        self._flushOccurences()

        
    """ get all FileNode subnodes of this node """
    def getFiles(self):
        self._makePersistent()
        dbfiles = db.getFiles(self.id)
        files = []
        for filename,type,mimetype in dbfiles:
            files += [FileNode(filename,type,mimetype,self)]
        return files
    

    """ add a FileNode to this node """
    def addFile(self, file):
        changed_metadata(self)
        self._makePersistent()
        db.addFile(self.id,file._path,file.type,file.mimetype)
        file.node = self
        file._add()


    """ remove a FileNode from this node """
    def removeFile(self, file):
        changed_metadata(self)
        self._makePersistent()
        db.removeFile(self.id,file._path)
        file._delete()


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

    def hasChild(self, name):
        try:
            self.getChild(name)
            return 1
        except NoSuchNodeError:
            return 0

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
            raise NoSuchNodeError("child:"+str(name))
        return getNode(str(id))
        
    def getContainerChildren(self):
        id = db.getContainerChildren(self.id)
        return NodeList(id)
        
    def getContentChildren(self):
        id = db.getContentChildren(self.id)
        return NodeList(id)


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
        f = self.getoverloadedfunction("event_metadata_changed")
        if f:
            f()


    """ get formated gps information """
    def get_location(self):
        exif_lon = self.get("exif_GPS_GPSLongitude")
        exif_lon_ref = self.get("exif_GPS_GPSLongitudeRef")
        exif_lat = self.get("exif_GPS_GPSLatitude")
        exif_lat_ref = self.get("exif_GPS_GPSLatitudeRef")
        
        if exif_lon=="" or exif_lon_ref=="" or exif_lat=="" or exif_lat_ref=="":
            return {}
         
        lon = float_from_gps_format(exif_lon)
        if exif_lon_ref=="W":
            lon *= -1;
            
        lat = float_from_gps_format(exif_lat)
        if exif_lat_ref=="S":
            lat *= -1;
        return {"lon":lon, "lat":lat}
    
    
    """ get a metadate """
    def get(self, name):
        if name.startswith('node'):
            if name in ["nodename", "node.name"]:
                return self.getName()        
            elif name=='node.id':
                return self.id
            elif name=='node.type':
                return self.type
            elif name=='node.orderpos':
                return self.orderpos            
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
            if isinstance(value, unicode):
                self.attributes[name] = value
            else:
                self.attributes[name] = str(value)

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
        self.ccount = -1
        for p in self.getParents():
            p._flushOccurences()

    def getAllOccurences(self, access):
        level = access.getPrivilegeLevel()
        if level not in self.occurences:
            self.occurences[level] = {}
            self.occurences2node[level] = {}
            nodelist = self.getAllChildren()
            if level>0:
                nodelist = access.filter(nodelist)
            for node in nodelist:
                schema = node.getSchema()
                if schema not in self.occurences[level]:
                    self.occurences[level][schema] = 1
                    self.occurences2node[level][schema] = node
                else:
                    self.occurences[level][schema] += 1
        ret = {}
        for s,v in self.occurences[level].items():
            if level in self.occurences2node and s in self.occurences2node[level]:
                ret[self.occurences2node[level][s]]=v
            else:
                print "not found", s
        return ret
    
    """ run a search query. returns a list of nodes """
    def search(self, q):
        global searcher, subnodes
        log.info('search: %s for node %s %s' %(q, str(self.id), str(self.name)))
        self._makePersistent()
        items = subnodes(self)
        if type(items)!= list:
            items = items.getIDs() 
        return NodeList(intersection([items, searcher.query(q)]))

    def __getattr__(self, name):
        cls = self.__class__
        if name in cls.__dict__:
            return cls.__dict__[name]
        if name in self.__dict__:
            return self.__dict__[name]
        f = self.getoverloadedfunction(name)
        if f:
            return f
                
        if self.attributes is None and self.id:
            self.attributes = db.getAttributes(self.id)
        if name in self.attributes:
            return self.attributes[name]

        if self.getContentType() in nodeclasses:
            raise AttributeError("Node of type '"+self.type+"' has no attribute '"+name+"'")
        else:
            raise AttributeError("Node of type '"+self.type+"' has no attribute '"+name+"' (type not overloaded)")

    def getoverloadedfunction(self, name):
        global nodefunctions,nodeclasses
        if self.getContentType() in nodeclasses:
            cls = nodeclasses[self.getContentType()]
            def r(cls):
                if name in cls.__dict__:
                    return lambda *x,**y: cls.__dict__[name](self, *x,**y)
                else:
                    for base in cls.__bases__:
                        if base.__name__!=self.__class__.__name__:
                            ret = r(base)
                            if ret:
                                return ret
                    return None
            ret = r(nodeclasses[self.getContentType()])
            if ret:
                return ret
        if name in nodefunctions:
            return lambda *x,**y: nodefunctions[name](self, *x,**y)
        return None

    
    # fill hashmap with idlists of listvalues
    def getAllAttributeValues(self, attribute, access, schema=""):
        values = {}
        try:
            if schema!="":
                sql = 'select distinct(value) from node, nodeattribute where node.id=nodeattribute.nid and nodeattribute.name="'+attribute+'" and node.type like "%/'+schema+'"'
                fields = db.runQuery(sql)
            else:
                fields = db.getMetaFields(attribute)
        except:
            fields = db.getMetaFields(attribute)

        # REVERT BACK TO SIMPLE SQL QUERY BECAUSE BELOW CODE TOO *SLOW*
        # MK/2008/10/27
        #fields = db.getMetaFields(attribute)
        for f in fields:
            for s in f[0].split(";"):
                s = u(s.strip())
                values[s] = values.get(s,0)+1
        return values

        ALL = -1
            
        self.lock.acquire() #FIXME: this lock is aquired way too long
        try:
            if not hasattr(self, 'attrlist') or attribute not in self.attrlist.keys():
                self.attrlist = {}
                self.attrlist[attribute] = {}
                
                # current attribute not listed -> create id list
                if not ALL in self.attrlist[attribute].keys():
                    self.attrlist[attribute][ALL] = {}            
                    ret = {}

                    # TODO: optimize this
                    for node in self.getAllChildren():
                        v = node.get(attribute)
                        if v not in ret.keys():
                            ret[v] =[]
                        ret[v].append(node.id)

                    for key in ret.keys():
                        self.attrlist[attribute][ALL][key] = NodeList(ret[key], key)
        finally:
            self.lock.release()

        level = access.getPrivilegeLevel()
        if not level in self.attrlist[attribute].keys():
            self.attrlist[attribute][level] = {}
            for item in self.attrlist[attribute][ALL].keys():
                if level==0:
                    l = self.attrlist[attribute][ALL][item]
                else:
                    l = self.attrlist[attribute][ALL][item].filter(access)
                self.attrlist[attribute][level][item] = len(l)
        return self.attrlist[attribute][level]

    #def getTechnAttributes(self):
    #    return {}
            
    
    def overwriteAccess(self, newrule, oldrule):
        """ Replaces the old access with new accessname"""
        """ Oldname is the old rules name
            Newname is the new rules name
            newrule is the actual new rule
            oldrule is the actual old rule"""
        tree_lock.acquire()
        try:
            oldrulestr = oldrule.getRuleStr()[1:-1].strip()
            newrulestr = newrule.getRuleStr()[1:-1].strip()

            if self.read_access:
                self.read_access = self.overwriteRule(self.read_access, oldrule.getName(), newrule.getName(), oldrulestr, newrulestr)
                if self.id:
                    pass
                    db.setNodeReadAccess(self.id, self.read_access)

            if self.write_access:
                self.write_access = self.overwriteRule(self.write_access, oldrule.getName(), newrule.getName(), oldrulestr, newrulestr)
                if self.id:
                    pass
                    db.setNodeWriteAccess(self.id,self.write_access)

            if self.data_access:
                self.data_access = self.overwriteRule(self.data_access, oldrule.getName(), newrule.getName(), oldrulestr, newrulestr)
                if self.id:
                    pass
                    db.setNodeDataAccess(self.id,self.data_access)
        finally:
            tree_lock.release()
            self.invalidateLocalRead()

            
    def overwriteRule(self, rulestring, oldname, newname, oldrulestr, newrulestr):
        """ rulestring is the access string, holding all access rules of this node
            Oldname is the old rule name
            newname is the new rule name
            oldrulestr is the old rule string
            newrulestr is the new rule string """
        rules = rulestring.split(",")
        result = []

        for r in rules:
            if r==oldname and not oldname=="":
                #Either its exactly the rulename
                r = newname
                
            elif oldrulestr in r and not oldrulestr=="":
                #Or its the rule string. There it first tests, if it is within the current rule. If it is there, it is tested, if it is exactly the rule.
                temp = r
                if temp.startswith("{"):
                    temp = temp[1:len(r)-1]
                    if temp.startswith("("):
                        temp = temp[1:len(r)-1]
                if temp==oldrulestr:
                    r = r.replace(oldrulestr, newrulestr)
            result.append(r)
        result = ",".join(result)
        return result        
   
            
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
    #if hasattr(nodeclass,'getLabels'):
    #    nodeclass.getLabels()

def registerNodeFunction(name, nodefunction):
    global nodefunctions
    nodefunctions[name] = nodefunction

def registerFileHandler(handler):
    global filehandlers
    filehandlers += [handler]

schema = None
subnodes = None
searchParser = None
searcher = None

def initialize(load=1):
    global db,_root,nodes_cache,testmode
    nodes_cache = MaxSizeDict(int(config.get("db.cache_size","100000")), keep_weakrefs=1)
    testmode = config.get("host.type", "") == "testing"
    db = database.getConnection()
    db.applyPatches()
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
        
        
    # load char replacement table

    file = None
    sections = ["chars", "words"]
    data = {"chars":[], "words":[]}
    for f in getRoot().getFiles():
        if f.retrieveFile().endswith("searchconfig.txt"):
            file = f
            break
            
    if file and os.path.exists(file.retrieveFile()):
        section = ""
        for line in open(file.retrieveFile(), "r"):
            line = line[:-1]
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
                continue
            if section in sections:
                data[section].append(line.split("="))
    import utils.utils
    utils.utils.normalization_items = data
