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
from utils.utils import get_filesize, intersection, u, float_from_gps_format
from utils.log import logException
from core.node import Node
from core.db import database
import logging
import time
import os
from utils.utils import get_hash
from utils.date import format_date, parse_date, STANDARD_FORMAT, now
from utils.lrucache import lru_cache
from locale import setlocale, strxfrm, LC_COLLATE, getlocale
import core.config as config
import thread
import traceback
from utils.compat import iteritems, string_types
import codecs

nodeclasses = {}
nodefunctions = {}
filehandlers = []

_root = None
db = None
bulk = 0
testmode = 0
nocache = 0

log = logg = logging.getLogger("backend")

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


@lru_cache(maxsize=100000)
def _get_node(id):
    return Node(dbid=id)


def getNode(id):
    try:
        lid = long(id)
    except ValueError:
        raise NoSuchNodeError(id)
    except TypeError:
        raise NoSuchNodeError(id)
    return _get_node(lid)


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

def getDirtySchemaNodes(num=0):
    return NodeList(db.getDirtySchemas(num))


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


class NodeList:
    def __init__(self, ids, description=""):
        if isinstance(ids, NodeList):
            ids = ids.ids
        elif len(ids) and isinstance(ids[0], Node):
            nodes = ids
            ids = [None]*len(nodes)
            for i,n in enumerate(nodes):
                ids[i]=n.id
        self.ids = [str(i) for i in ids]
        self.len = len(ids)
        self.description = description
    def __len__(self):
        return self.len
    def __getitem__(self, i):
        if type(i) == slice:
            nodes = []
            for id in self.ids[i]:
                nodes += [getNode(id)]
            return nodes
        elif i >= self.len:
            raise IndexError(str(i)+" >= "+str(self.len))
        return getNode(self.ids[i])

    def getIDs(self):
        return self.ids

    def getDescription(self):
        return self.description

    def sort_by_fields(self, field):
        if not field or not self.ids:
            return self
        if isinstance(field, str):
            # handle some special cases
            if field == "name" or field == "nodename":
                return self.sort_by_name("up")
            elif field == "-name" or field == "nodename":
                return self.sort_by_name("down")
            elif field in ("orderpos", "-orderpos"):
                raise NotImplementedError("this method must not be used for orderpos sorting!")
            else:
                # sort query function needs seq of sortfields, convert
                fields = [field]
        else:
            # remove empty sortfields
            fields = [f for f in field if f]
            if not fields:
                # no fields left, all empty...
                return self
        t1 = time.time()
        nids = ",".join("'" + i +  "'" for i in self.ids)
        sorted_nids = db.sort_nodes_by_fields(nids, fields)
        missing_nids = set(self.ids) - set(sorted_nids)
        if missing_nids:
            # query returned too few nids, add missing ids unsorted
            logg.info("fields missing for %s nodes when sorting by %s", len(missing_nids), fields)
#             logg.debug("node IDs with missing fields: %s", missing_nids)
            sorted_nids += missing_nids
        extra_nids = set(sorted_nids) - set(self.ids)
        if extra_nids:
            # query returned too many nids, remove extra nids
            logg.info("query return %s extra nids", len(extra_nids))
            sorted_nids = [i for i in sorted_nids if i not in extra_nids]
        self.ids = sorted_nids
        if log.isEnabledFor(logging.DEBUG):
            msg = "sorting for {} with {} ids took {} seconds".format(fields, len(self.ids), time.time()-t1)
            log.debug(msg)
        return self

    def sort_by_orderpos(self):
        nodes = [getNode(str(i)) for i in self.ids]
        nodes.sort(key=lambda n: n.orderpos)
        return nodes

    def sort_by_name(self, direction="up", locale=None):
        reverse = direction == "down"
        nodes = [getNode(str(i)) for i in self.ids]
        # set locale and restore current value after sorting if given
        if locale:
            last_locale = getlocale(LC_COLLATE)
            setlocale(locale)
        nodes.sort(key=lambda n: strxfrm(n.name), reverse=reverse)
        if locale:
            setlocale(LC_COLLATE, last_locale)
        # we don't return a NodeList here, but a normal
        # list. The main difference between those two is
        # that a normal list doesn't have an "intersect" operation.
        # That's ok because we don't want to intersect sorted
        # lists.
        return nodes

    def filter(self, access):
        return access.filter(self)

def _set_attribute_complex(node, name, value):
    if isinstance(value, string_types):
        db.setAttribute(node.id, name, codecs.encode(value, "utf8"), check=(not bulk))
    else:
        db.set_attribute_complex(node.id, name, value, check=(not bulk))


        ### methods to patch in for Node which store complex attributes
def _node_set_complex(self, name, value):
    """Set an attribute, new version.
    Passes unmodified values to the DB connector, converts unicode objects to utf8 strings.
    """
    if name == "nodename":
        return self.setName(value)
    self.attributes[name] = value
    if self.id:
        _set_attribute_complex(self, name, value)


def _node_make_persistent_complex(self):
    if self.id is None:
        changed_metadata(self)
        tree_lock.acquire()
        try:
            self.id = db.createNode(self.name,self.type)
            for name, value in self.attributes.items():
                _set_attribute_complex(self, name, value)
            if self.read_access:
                db.setNodeReadAccess(self.id,self.read_access)
            if self.write_access:
                db.setNodeWriteAccess(self.id,self.write_access)
            if self.data_access:
                db.setNodeDataAccess(self.id,self.data_access)
        finally:
            tree_lock.release()


def _node_load_attributes_complex(nid):
    return db.get_attributes_complex(nid)


class NodeMeta(type):
    """print methods of node subclasses and warn if Node methods are overriden"""
    def __init__(cls, name, bases, dct):
        # patch methods for attribute handling to support complex values
        if cls._store_complex_attributes:
            cls._load_attributes = staticmethod(_node_load_attributes_complex)
            cls.set = _node_set_complex
            cls._makePersistent = _node_make_persistent_complex
        #print methods of node subclasses and warn if Node methods are overriden
#         if name != "Node":
#             print("\ncls " + name)
#             print("=" * (len(name) + 4))
#             for k in dct.keys():
#                 if k in ["__module__", "__doc__"]:
#                     continue
#                 redefined = k in Node.__dict__
#                 msg = "redefined!" if redefined else "ok"
#                 out = sys.stderr if redefined else sys.stdout
#                 r = "{}: {}".format(k, msg)
#                 print >> out, r
        super(NodeMeta, cls).__init__(name, bases, dct)


def remove_from_nodecaches(node):
    nid = long(node.id)
    del childids_cache[nid]
    del parentids_cache[nid]
    _get_node.cache_remove(nid)


def flush():
    global childids_cache, parentids_cache, _root, db
    tree_lock.acquire()
    try:
        childids_cache = None
        _get_node.cache_clear()
        parentids_cache = None
        db = database.getConnection()
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
    global db, _root, testmode
    testmode = config.get("host.type", "") == "testing"
    db = database.getConnection()
    if load:
        getRoot()
    global schema, subnodes, searchParser, searcher
    import schema.schema as schema
    from core.search.ftsquery import DBTYPE
    schema = schema

    if config.get("config.searcher","")=="fts3": # use fts3

        from core.search.ftsquery import subnodes, ftsSearcher
        from core.search.ftsparser import ftsSearchParser

        subnodes = subnodes
        searchParser = ftsSearchParser
        searcher = ftsSearcher

        def getTablenames(searcher, schema, db_type):
            tablenames = []
            res = searcher.execute("SELECT * FROM sqlite_master WHERE type='table'", schema, db_type)
            if res is not None:
                tablenames += [t[1] for t in res]
            return tablenames

        # check fts database for tables
        msg = "looking for tables in sqlite database of the searcher ..."
        log.info(msg)
        for schema in searcher.schemas:
            for db_type in list(set(searcher.connames[DBTYPE].values())):
                try:
                    tablenames = getTablenames(searcher, schema, db_type)
                    if tablenames:
                        msg = "found %d tables in sqlite database of the searcher: %r" % (len(tablenames), tablenames)
                        log.info(msg)
                        print "fts3 searcher initialized"
                    else:
                        msg = "found no tables in sqlite database of the searcher ... trying to initialize database"
                        log.warning(msg)
                        searcher.initIndexer(option="init")
                        tablenames = getTablenames(searcher, schema, db_type)
                        if tablenames:
                            msg = "found %d tables in newly initialized sqlite database of the searcher: %r" % (len(tablenames), tablenames)
                            log.info(msg)
                            print "fts3 searcher initialized"
                        else:
                            raise
                except:
                    msg = "could not query tables from fts sqlite database ... searcher may not be functional"
                    log.error(msg)

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
