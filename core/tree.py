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
from utils import *
import config
import os
nodeclasses = {}
nodefunctions = {}

noimpl = "No Implementation loaded"

def getNode(id):
    raise noimpl

def getRoot(name=None):
    raise noimpl

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

class NoSuchNodeError:
    def __init__(self,id=None):
        self.id = id
    def __str__(self):
        return "NoSuchNodeError("+str(self.id)+")"

class InvalidOperationError:
    pass

class NodeList:
    def sort(self,field=""):
        raise noimpl
    def intersect(self,other):
        raise noimpl
    def getDescription(self):
        raise noimpl

class NodeType:
    def getMetaFields():
        raise noimpl

def getType(name):
    raise noimpl


class Node:
    def __init__(self, name="<unbenannt>", type=None, id=None):
        raise noimpl
    
    """ get the node name """
    def getName(self):
        raise noimpl
    
    """ set the node name """
    def setName(self):
        raise noimpl
    
    """ get the node type """
    def getType(self):
        raise noimpl
    
    """ get the node type (as string) """
    def getTypeName(self):
        raise noimpl
    
    """ set the node type (as string) """
    def setTypeName(self):
        raise noimpl
    
    """ get the position of this node """
    def getOrderPos(self):
        raise noimpl

    """ set the position that this node appears in nodelists """
    def setOrderPos(self, nr):
        raise noimpl
    
    """ get a named access right (e.g. read, write, etc.)"""
    def getAccess(self, type):
        raise noimpl

    """ set a named access right (e.g. read, write, etc.)"""
    def setAccess(self, type, access):
        raise noimpl
    
    """ add a child node """
    def addChild(self,c):
        raise noimpl
    
    """ remove (unlink) a given child node """
    def removeChild(self,c):
        raise noimpl

    """ get a child with a specific node name """
    def getChild(self):
        raise noimpl

    """ get all direct children of this node """
    def getChildren(self):
        raise noimpl
   
    """ get the number of direct children of this node """
    def getNumChildren(self):
        raise noimpl

    """ get all decendants of this node """
    def getAllChildren(self):
        raise noimpl

    """ get all parents of this node """
    def getParents(self):
        raise noimpl

    """ get all FileNode subnodes of this node """
    def getFiles(self):
        raise noimpl

    """ add a FileNode to this node """
    def addFile(self, file):
        raise noimpl

    """ remove a FileNode from this node """
    def removeFile(self, file):
        raise noimpl

    """ get a metadate """
    def get(self, name):
        raise noimpl

    """ set a metadate """
    def set(self, name, value):
        raise noimpl

    """ get all metadates (key/value) pairs """
    def items(self):
        raise noimpl

    """ get the number of descendants of all types (hashtable) """
    def getAllOccurences(self):
        raise noimpl

    """ run a search query. returns a list of nodes """
    def search(self,query):
        raise noimpl
   
def flush():
    pass

def registerNodeClass(type, nodeclass):
    global nodeclasses
    nodeclasses[type] = nodeclass

def registerNodeFunction(nodefunction):
    global nodefunctions
    nodefunctions[nodefunction.__name__] = nodefunction

def setImplementation(module, load=1):
    global Node,getNode,getRoot,getType,flush,FileNode,NodeList
    module.initialize(load)
    Node = module.Node
    if "FileNode" in dir(module):
        FileNode = module.FileNode
    if "NodeList" in dir(module):
        NodeList = module.NodeList
    getNode = module.getNode
    getRoot = module.getRoot
    getType = module.getType
    flush = module.flush

