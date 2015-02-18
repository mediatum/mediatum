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
from utils.strings import ensure_unicode

nodeclasses = {}
nodefunctions = {}
filehandlers = []

_root = None
db = None
bulk = 0
testmode = 0
nocache = 0

logg = logging.getLogger(__name__)

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
                logg.exception("Lock acquired more than once!")
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


def getAllContainerChildrenNum(node, count=0):  # returns the number of children
    for n in node.getContainerChildren():
        count = getAllContainerChildrenNum(n, count)
    count += len(node.getContentChildren())
    return count


def getAllContainerChildrenAbs(node, count=[]):  # returns a list with children, each child once
    for n in node.getContainerChildren():
        count = getAllContainerChildrenAbs(n, count)
    count.extend(node.getContentChildren().ids)
    return count


def getAllContainerChildren(node):
    return len(list(set(getAllContainerChildrenAbs(node, []))))  # get number of children
    # return getAllContainerChildrenNum(node, 0) # get number of children (faster)
    # return 0 # suppress number (fastest)


def getNodesByAttribute(attributename, attributevalue=u""):
    return db.getNodeIdByAttribute(attributename, attributevalue)


def getDirtyNodes(num=0):
    return NodeList(db.getDirty(num))


def getDirtySchemaNodes(num=0):
    return NodeList(db.getDirtySchemas(num))


class NoSuchNodeError:

    def __init__(self, id=None):
        self.id = id

    def __str__(self):
        return "NoSuchNodeError(%s)" % self.id


class InvalidOperationError:
    pass


class FileNode:

    def __init__(self, name, type, mimetype, node=None):
        if name.startswith(config.settings["paths.datadir"]):
            name = name[len(config.settings["paths.datadir"]):]
        self._path = name
        # self.path = name # workaround, until CVS is updated everywhere
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
                    logg.exception("file handler add() failed")

    def _delete(self):
        for f in filehandlers:
            if hasattr(f, "delete"):
                try:
                    if f.delete(self):
                        return
                except:
                    logg.exception("file handler delete() failed")

    def retrieveFile(self):
        for f in filehandlers:
            if hasattr(f, "retrieveFile"):
                try:
                    path = f.retrieveFile(self)
                    if path:
                        return path
                except:
                    logg.exception("file handler retrieveFile() failed")

        if os.path.exists(self._path):
            return self._path

        if os.path.exists(config.basedir + "/" + self._path):
            return config.basedir + "/" + self._path

        if not os.path.exists(config.settings["paths.datadir"] + self._path):
            for f in self.node.getFiles():
                if f.getType().startswith("presentati"):
                    try:
                        #_n = os.path.dirname(f.retrieveFile())+"/"+self._path
                        _n = os.path.dirname(f._path) + "/" + self._path
                        if os.path.exists(_n):
                            return _n
                    except:
                        logg.exception("exception in retrieveFile, ignore")
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
                    logg.exception("file handler getSize() failed, return -1")
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
                    logg.exception("file handler getHash() failed")
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

    def __init__(self, ids, description=u""):
        if isinstance(ids, NodeList):
            ids = ids.ids
        elif len(ids) and isinstance(ids[0], Node):
            nodes = ids
            ids = [None] * len(nodes)
            for i, n in enumerate(nodes):
                ids[i] = n.id
        self.ids = ids
        self.len = len(ids)
        self.description = description

    def __len__(self):
        return self.len

    def __getitem__(self, i):
        if isinstance(i, slice):
            nodes = []
            for id in self.ids[i]:
                nodes += [getNode(id)]
            return nodes
        elif i >= self.len:
            raise IndexError("%s >= %s" % (i, self.len))
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
        nids = ",".join('\'%s\'' % i for i in self.ids)
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
        if logg.isEnabledFor(logging.DEBUG):
            logg.debug("sorting for %s with %s ids took %s seconds", fields, len(self.ids), time.time() - t1)
        return self

    def sort_by_orderpos(self):
        nodes = [getNode(i) for i in self.ids]
        nodes.sort(key=lambda n: n.orderpos)
        return nodes

    def sort_by_name(self, direction="up", locale=None):
        reverse = direction == "down"
        nodes = [getNode(i) for i in self.ids]
        # set locale and restore current value after sorting if given
        if locale:
            last_locale = getlocale(LC_COLLATE)
            setlocale(locale)
        nodes.sort(key=lambda n: strxfrm(n.name.encode("utf8")), reverse=reverse)
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


# methods to patch in for Node which store complex attributes

def _set_attribute_complex(node, name, value):
    db.set_attribute_complex(node.id, name, value, check=(not bulk))


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
            self.id = db.createNode(self.name, self.type)
            for name, value in self.attributes.items():
                _set_attribute_complex(self, name, value)
            if self.read_access:
                db.setNodeReadAccess(self.id, self.read_access)
            if self.write_access:
                db.setNodeWriteAccess(self.id, self.write_access)
            if self.data_access:
                db.setNodeDataAccess(self.id, self.data_access)
            # add node to cache to avoid "ghost nodes" (multiple objects for a single database row)
            _get_node.cache_add(self, long(self.id))
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
        # print methods of node subclasses and warn if Node methods are overriden
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


class Node(object):
    __metaclass__ = NodeMeta
    # non string arguments will be saved in msgpack format if store_complex_attributes is True
    _store_complex_attributes = False

    def __new__(cls, name=u"<noname>", type=None, dbid=None):
        if dbid:
            dbnode = db.getNode(dbid)
            if not dbnode:
                raise NoSuchNodeError(dbid)
            id, name, type, read, write, data, orderpos, localread = dbnode
        # find matching node class
        try:
            nodetype = type.split("/", 1)[0]
        except:
            logg.warn("no type given for instance of %s with name %s", cls, name)
        else:
            nodecls = nodeclasses.get(nodetype)
            if nodecls:
                #                 logg.debug("found matching nodeclass: %s for type %s", nodecls, type)
                cls = nodecls
            else:
                pass
#                 logg.debug("no matching nodeclass for type %s", type)
        obj = object.__new__(cls)
        if dbid:
            obj.id = id
            attrs = cls._load_attributes(id)
            obj.attributes = attrs
            obj._name = ensure_unicode(name)
            obj.type = type
            obj.prev_nid = attrs.get('system.prev_id', '0')
            obj.next_nid = attrs.get('system.next_id', '0')
            obj.read_access = read
            obj.write_access = write
            obj.data_access = data
            obj.orderpos = orderpos
            obj.localread = localread
        return obj

    def __init__(self, name=u"<noname>", type=None, dbid=None):
        self.occurences = None
        self.lock = thread.allocate_lock()  # for attrlist
        if dbid is None:
            if type is None:
                raise "Node must have a type"
            self.id = None
            self.prev_nid = '0'
            self.next_nid = '0'
            if name is None:
                self._name = u""
            else:
                self._name = ensure_unicode(name)
            self.type = type
            self.read_access = None
            self.write_access = None
            self.data_access = None
            self.orderpos = 1
            self.attributes = {}
            self.localread = None
            if type == "root":
                self._makePersistent()

        self.occurences = {}
        self.occurences2node = {}
        self.ccount = -1

    @staticmethod
    def _load_attributes(nid):
        return db.getAttributes(nid)

    @property
    def unicode_name(self):
        return self._name

    def _makePersistent(self):
        if self.id is None:
            changed_metadata(self)
            tree_lock.acquire()
            try:
                self.id = db.createNode(self.name, self.type)
                for name, value in self.attributes.items():
                    db.setAttribute(self.id, name, value, check=(not bulk))
                if self.read_access:
                    db.setNodeReadAccess(self.id, self.read_access)
                if self.write_access:
                    db.setNodeWriteAccess(self.id, self.write_access)
                if self.data_access:
                    db.setNodeDataAccess(self.id, self.data_access)
                # add node to cache to avoid "ghost nodes" (multiple objects for a single database row)
                _get_node.cache_add(self, long(self.id))
            finally:
                tree_lock.release()

    def setNextID(self, id):
        self.next_nid = id
        self.set('system.next_id', id)

    def setPrevID(self, id):
        self.prev_nid = id
        self.set('system.prev_id', id)

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
        return self._name

    """ set the node name """

    def setName(self, name):
        self._name = ensure_unicode(name)
        if self.id:
            db.setNodeName(self.id, name)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self.setName(name)

    """ get the position of this node """

    def getOrderPos(self):
        return self.orderpos

    """ set the position that this node appears in nodelists """

    def setOrderPos(self, orderpos):
        self._makePersistent()
        self.orderpos = orderpos
        db.setNodeOrderPos(self.id, orderpos)

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
            return self.type[self.type.find('/') + 1:]
        else:
            return self.type

    def invalidateLocalRead(self):
        self.localread = u""
        if self.id:
            db.setNodeLocalRead(self.id, self.localread)
        for c in self.getChildren():
            c.invalidateLocalRead()

    def getLocalRead(self):
        if not self.localread:
            if self.id is None:
                return self.read_access

            def p(node, rights):
                r = node.read_access
                if r:
                    for rule in r.split(","):
                        rights[rule] = None
                else:
                    for c in node.getParents():
                        p(c, rights)
            rights = {}
            p(self, rights)
            self.localread = ",".join(rights.keys())
            db.setNodeLocalRead(self.id, self.localread)
        return self.localread

    def resetLocalRead(self):
        self.localread = u""
        db.setNodeLocalRead(self.id, self.localread)

    """ set the node type (as string) """

    def setTypeName(self, type):
        changed_metadata(self)
        self.type = type
        if self.id:
            db.setNodeType(self.id, type)
            self._flushOccurences()

    def setSchema(self, schema):
        doctype = self.getContentType()
        if schema:
            self.setTypeName(doctype + "/" + schema)
        else:
            self.setTypeName(doctype)

    def setContentType(self, doctype):
        if "/" in self.type:
            schema = self.getSchema()
            self.setTypeName(doctype + "/" + schema)
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
                    db.setNodeReadAccess(self.id, access)
            elif type == "write":
                self.write_access = access
                if self.id:
                    db.setNodeWriteAccess(self.id, access)
            elif type == "data":
                self.data_access = access
                if self.id:
                    db.setNodeDataAccess(self.id, access)
        finally:
            tree_lock.release()
        if self.id and type == "read":
            self.invalidateLocalRead()

    def _flush(self):
        global childids_cache, parentids_cache
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

    def addChild(self, child):
        self._makePersistent()
        child._makePersistent()
        self._flush()
        child._flush()

        if self.id == child.id or self.id in child._getAllChildIDs():
            raise InvalidOperationError()

        db.addChild(self.id, child.id, check=(not bulk))
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
        db.removeChild(self.id, child.id)
        child.resetLocalRead()
        self._flushOccurences()

    """ get all FileNode subnodes of this node """

    def getFiles(self):
        self._makePersistent()
        dbfiles = db.getFiles(self.id)
        files = []
        for filename, type, mimetype in dbfiles:
            files += [FileNode(filename, type, mimetype, self)]
        return files

    """ add a FileNode to this node """

    def addFile(self, file):
        changed_metadata(self)
        self._makePersistent()
        db.addFile(self.id, file._path, file.type, file.mimetype)
        file.node = self
        file._add()

    """ remove a FileNode from this node """

    def removeFile(self, file, single=False):
        changed_metadata(self)
        self._makePersistent()
        if single:
            db.removeSingleFile(self.id, file._path)
        else:
            db.removeFile(self.id, file._path)
        file._delete()

    def _mkCache(self, source):
        cache = {}
        lastid = None
        list = []
        for id, childid in source:
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
        global childids_cache, parentids_cache
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

    def get_children_with_type(self, nodetype):
        return NodeList(db.get_children_with_type(self.id, nodetype))

    """ get a child with a specific node name """

    def getChild(self, name):
        if name is None:
            raise NoSuchNodeError("child:None")
        if not self.id:
            raise NoSuchNodeError("child of None")
        id = db.getNamedNode(self.id, name)
        if not id:
            raise NoSuchNodeError("child:" + name)
        return getNode(id)

    def get_child_with_type(self, name, nodetype):
        """Returns a child with specific name and nodetype."""
        if name is None:
            raise NoSuchNodeError("child:None")
        if not self.id:
            raise NoSuchNodeError("child of None")
        nid = db.getNamedTypedNode(self.id, name, nodetype)
        if not nid:
            raise NoSuchNodeError("child:" + name)
        return getNode(nid)

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
        global childids_cache, parentids_cache
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
                self._getAllChildIDs(id, map, 1)
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

    """ get formated gps information """

    def get_location(self):
        exif_lon = self.get("exif_GPS_GPSLongitude")
        exif_lon_ref = self.get("exif_GPS_GPSLongitudeRef")
        exif_lat = self.get("exif_GPS_GPSLatitude")
        exif_lat_ref = self.get("exif_GPS_GPSLatitudeRef")

        if exif_lon == "" or exif_lon_ref == "" or exif_lat == "" or exif_lat_ref == "":
            return {}

        lon = float_from_gps_format(exif_lon)
        if exif_lon_ref == "W":
            lon *= -1

        lat = float_from_gps_format(exif_lat)
        if exif_lat_ref == "S":
            lat *= -1
        return {"lon": lon, "lat": lat}

    """ get a metadate """

    def get(self, name):
        if name.startswith('node'):
            if name in ["nodename", "node.name"]:
                return self.getName()
            elif name == 'node.id':
                return self.id
            elif name == 'node.type':
                return self.type
            elif name == 'node.orderpos':
                return self.orderpos
        return self.attributes.get(name, u"")

    """ set a metadate """

    def set(self, name, value):
        if name == "nodename":
            return self.setName(value)
        if self.attributes is None:
            if not self.id:
                raise "Internal Error"
        else:
            self.attributes[name] = ensure_unicode(value)

        if self.id:
            db.setAttribute(self.id, name, value, check=(not bulk))

    """ get all metadates (key/value) pairs """

    def items(self):
        return self.attributes.items()

    def setAttribute(self, name, value):
        self.set(name, value)

    def getAttribute(self, name):
        return self.get(name)

    def removeAttribute(self, name):
        if self.attributes:
            try:
                del self.attributes[name]
            except KeyError:
                pass
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
            if level > 0:
                nodelist = access.filter(nodelist)
            for node in nodelist:
                schema = node.getSchema()
                if schema not in self.occurences[level]:
                    self.occurences[level][schema] = 1
                    self.occurences2node[level][schema] = node
                else:
                    self.occurences[level][schema] += 1
        ret = {}
        for s, v in self.occurences[level].items():
            if level in self.occurences2node and s in self.occurences2node[level]:
                ret[self.occurences2node[level][s]] = v
            else:
                logg.warn("getAllOccurences: not found %s", s)
        return ret

    """ run a search query. returns a list of nodes """

    def search(self, q):
        global searcher, subnodes
        logg.info('search: %s for node %s %s', q, self.id, self.name)
        self._makePersistent()
        if q.startswith('searchcontent='):
            return searcher.query(q)
        items = subnodes(self)
        if not isinstance(items, list):
            items = items.getIDs()
        return NodeList(intersection([items, searcher.query(q)]))

    def __getattr__(self, name):
        cls = self.__class__
        if name in cls.__dict__:
            logg.warn("DEPRECATED: class attribute accessed by (%s).__getattr__(%s)", self, name)
            return cls.__dict__[name]
        if name in self.__dict__:
            logg.warn("DEPRECATED: instance attribute accessed by (%s).__getattr__(%s)", self, name)
            return self.__dict__[name]
        if name in self.attributes:
            return self.attributes[name]

        if name in nodefunctions:
            return lambda *x, **y: nodefunctions[name](self, *x, **y)
        
        # fall-through
        raise AttributeError("Node %s of type has no attribute %s", self, name)


    # fill hashmap with idlists of listvalues
    def getAllAttributeValues(self, attribute, access, schema=u""):
        values = {}
        try:
            if schema != "":
                fields = db.get_all_attribute_values(attribute, schema, distinct=True)
            else:
                fields = db.getMetaFields(attribute)
        except:
            logg.exception("exception in getAllAttributeValues")
            fields = db.getMetaFields(attribute)

        # REVERT BACK TO SIMPLE SQL QUERY BECAUSE BELOW CODE TOO *SLOW*
        # MK/2008/10/27
        #fields = db.getMetaFields(attribute)
        for f in fields:
            for s in f[0].split(";"):
                s = s.strip()
                values[s] = values.get(s, 0) + 1
        return values

        ALL = -1

        self.lock.acquire()  # FIXME: this lock is aquired way too long
        try:
            if not hasattr(self, 'attrlist') or attribute not in self.attrlist.keys():
                self.attrlist = {}
                self.attrlist[attribute] = {}

                # current attribute not listed -> create id list
                if ALL not in self.attrlist[attribute].keys():
                    self.attrlist[attribute][ALL] = {}
                    ret = {}

                    # TODO: optimize this
                    for node in self.getAllChildren():
                        v = node.get(attribute)
                        if v not in ret.keys():
                            ret[v] = []
                        ret[v].append(node.id)

                    for key in ret.keys():
                        self.attrlist[attribute][ALL][key] = NodeList(ret[key], key)
        finally:
            self.lock.release()

        level = access.getPrivilegeLevel()
        if level not in self.attrlist[attribute].keys():
            self.attrlist[attribute][level] = {}
            for item in self.attrlist[attribute][ALL].keys():
                if level == 0:
                    l = self.attrlist[attribute][ALL][item]
                else:
                    l = self.attrlist[attribute][ALL][item].filter(access)
                self.attrlist[attribute][level][item] = len(l)
        return self.attrlist[attribute][level]

    # def getTechnAttributes(self):
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
                    db.setNodeWriteAccess(self.id, self.write_access)

            if self.data_access:
                self.data_access = self.overwriteRule(self.data_access, oldrule.getName(), newrule.getName(), oldrulestr, newrulestr)
                if self.id:
                    pass
                    db.setNodeDataAccess(self.id, self.data_access)
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
            if r == oldname and not oldname == "":
                # Either its exactly the rulename
                r = newname

            elif oldrulestr in r and not oldrulestr == "":
                # Or its the rule string. There it first tests, if it is within the
                # current rule. If it is there, it is tested, if it is exactly the rule.
                temp = r
                if temp.startswith("{"):
                    temp = temp[1:len(r) - 1]
                    if temp.startswith("("):
                        temp = temp[1:len(r) - 1]
                if temp == oldrulestr:
                    r = r.replace(oldrulestr, newrulestr)
            result.append(r)
        return ",".join(result)

    def createNewVersion(self, user):
        if self.get('system.version.id') == '':
            self.set('system.version.id', '1')

        n = Node(name=self.name, type=self.type)
        n.set("creator", self.get('creator'))
        n.set("creationtime", self.get('creationtime'))
        n.set("updateuser", user.getName())
        n.set("edit.lastmask", self.get('edit.lastmask'))

        if self.get('updatetime') < unicode(now()):
            n.set("updatetime", format_date())
        else:
            n.set("updatetime", self.get('updatetime'))

        for f in self.getFiles():
            n.addFile(f)

        activeNode = self.getActiveVersion()
        for pid in db.getParents(activeNode.id):
            parentNode = getNode(pid)
            parentNode.addChild(n)
            parentNode.removeChild(activeNode)

        for cid in db.getChildren(activeNode.id):
            if cid != activeNode.prev_nid:
                n.addChild(getNode(cid))
        n.set("system.version.id", self.getLastVersionID() + 1)

        n.setPrevID(activeNode.id)
        activeNode.setNextID(n.id)
        n.addChild(activeNode)
        return n

    def getActiveVersion(self):
        node = self
        _node = node
        while _node.next_nid and _node.next_nid != '0' and _node.next_nid != _node.id:
            _node = getNode(_node.next_nid)
            if _node.get("deleted") != "true":
                node = _node
        return node

    def isActiveVersion(self):
        return self.get("system.next_id") in ['', '0']

    def getLastVersionID(self):
        last_version_id = 1
        node = self.getActiveVersion()
        version_id = node.get("system.version.id")
        if version_id != "":
            last_version_id = int(version_id)

        while node.prev_nid and node.prev_nid != '0':
            node = getNode(node.prev_nid)
            version_id = node.get("system.version.id")
            if version_id != "":
                if int(version_id) > last_version_id:
                    last_version_id = int(version_id)
        return last_version_id

    def getVersionList(self):
        node_versions = []
        node = self.getActiveVersion()
        if node.get("deleted") != "true":
            node_versions.append(node)
        while node.prev_nid and node.prev_nid != '0':
            node = getNode(node.prev_nid)
            if node.get("deleted") != "true":
                node_versions.append(node)

        for i in range(len(node_versions) - 1):
            nodei = node_versions[i]
            last_version_id = nodei.get("system.version.id")
            last_version_id = last_version_id != "" and int(last_version_id) or 1
            for j in range(i + 1, len(node_versions)):
                node = node_versions[j]
                version_id = node.get("system.version.id")
                version_id = version_id != "" and int(version_id) or 1
                if version_id > last_version_id:
                    last_version_id = version_id
                    node_versions[i] = node
                    node_versions[j] = nodei
                    nodei = node
        return node_versions

    def getUpdatedDate(self, format=None):
        if format is None:
            format = STANDARD_FORMAT
        if self.get('updatetime'):
            return format_date(parse_date(self.get('updatetime')), '%d.%m.%Y, %H:%M:%S')
        if self.get('creationtime'):
            return format_date(parse_date(self.get('creationtime')), '%d.%m.%Y, %H:%M:%S')
        return ''

    def __repr__(self):
        return u"Node<{}: '{}'> ({})".format(self.id, self.unicode_name, object.__repr__(self)).encode("utf8")

    # some additional methods from dict

    def __contains__(self, key):
        return key in self.attributes\
            or key in ('node', 'node.name', "nodename", "node.id", "node.type", "node.orderpos")

    def __getitem__(self, key):
        if key not in self:
            raise KeyError(key)
        return self.get(key)

    def __iter__(self):
        """iter() thinks that a Node is iterable because __getitem__ is implemented.
        That behaviour is stupid (legacy...), so we have to state explicitly that this thing is not iterable!
        """
        raise TypeError("not iterable!")

    def __len__(self):
        """
        :returns: number of attributes
        """
        return len(self.attributes)

    def __nonzero__(self):
        """Some code in mediaTUM relies on the fact that Node objects are always true, like `if user:`
        which is really a check if the user is not None.
        This can fail now because __len__ == 0 means that the Node object is false.
        Such code should be fixed (=> use `if user is None`). In the meantime, we just say that Node is always true.
        """
        return True

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        self.removeAttribute(key)

    def setdefault(self, key, value):
        """Same as dict.setdefault."""
        if key not in self:
            self.set(key, value)
            return value
        else:
            return self.get(key)

    # some helpers for interactive use
    @property
    def child_dict(self, type=None):
        child_nodes = [getNode(i) for i in self.children]
        child_dict = {c.name: c for c in child_nodes}
        return child_dict

    def child_dict_with_filter(self, nodefilter):
        child_nodes = [getNode(i) for i in self.children]
        child_dict = {c.name: c for c in child_nodes if nodefilter(c)}
        return child_dict

    def child_dict_with_type(self, type):
        nodefilter = lambda n: n.type == type or n.__class__.__name__ == type
        return self.child_dict_with_filter(nodefilter)

    @property
    def content_type(self):
        return self.getContentType()

    def attributes_filtered_by_key(self, attribute_key_filter):
        return {k: v for k, v in iteritems(self.attributes) if attribute_key_filter(k)}

    def attributes_filtered_by_value(self, attribute_value_filter):
        return {k: v for k, v in iteritems(self.attributes) if attribute_value_filter(v)}


def remove_from_nodecaches(node):
    nid = long(node.id)
    childids_cache[nid] = None
    parentids_cache[nid] = None
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
    # if hasattr(nodeclass,'getLabels'):
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
    db.applyPatches()
    if load:
        getRoot()
    global schema, subnodes, searchParser, searcher
    import schema.schema as schema
    from core.search.ftsquery import DBTYPE
    schema = schema

    if config.get("config.searcher", "") == "fts3":  # use fts3

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
        logg.info("looking for tables in sqlite database of the searcher")
        for schema in searcher.schemas:
            for db_type in list(set(searcher.connames[DBTYPE].values())):
                try:
                    tablenames = getTablenames(searcher, schema, db_type)
                    if tablenames:
                        logg.debug("found %d tables in sqlite database of the searcher: %r", len(tablenames), tablenames)
                    else:
                        logg.warn("found no tables in sqlite database of the searcher ... trying to initialize database")
                        searcher.initIndexer(option="init")
                        tablenames = getTablenames(searcher, schema, db_type)
                        if tablenames:
                            logg.info("found %d tables in newly initialized sqlite database of the searcher: %r", len(tablenames), tablenames)
                        else:
                            raise
                except:
                    logg.error("could not query tables from fts sqlite database ... searcher may not be functional")

    else:  # use magpy
        logg.info("magpy searcher initialized")
        from core.search.query import subnodes, mgSearcher
        from core.search.parser import searchParser

        subnodes = subnodes
        searchParser = searchParser
        searcher = mgSearcher

    # load char replacement table

    file = None
    sections = ["chars", "words"]
    data = {"chars": [], "words": []}
    for f in getRoot().getFiles():
        if f.retrieveFile().endswith("searchconfig.txt"):
            file = f
            break

    if file and os.path.exists(file.retrieveFile()):
        section = ""
        for line in codecs.open(file.retrieveFile(), "r", encoding='utf8'):
            line = line[:-1]
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
                continue
            if section in sections:
                data[section].append(line.split("="))
    import utils.utils
    utils.utils.normalization_items = data
