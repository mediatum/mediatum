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
import xml.parsers.expat as expat
import StringIO
import random

from utils.utils import esc, u

def writexml(node, fi, indent=None, written=None, children=True):
    if written is None:
        written = {}
    if indent is None:
        indent = 0
    fi.write((" "*indent) + '<node name="'+esc(node.name)+'" id="'+str(node.id)+'" ')
    if node.type is None:
        node.type="node"
    fi.write("type=\""+node.type+"\" ")
    if node.read_access:
        fi.write("read=\""+esc(node.read_access)+"\" ")
    if node.write_access:
        fi.write("write=\""+esc(node.write_access)+"\" ")
    if node.data_access:
        fi.write("data=\""+esc(node.data_access)+"\" ")
    fi.write('>'+"\n")

    indent += 4
        
    for name,value in node.items():
        fi.write((" "*indent) + '<attribute name="'+esc(name)+'"><![CDATA['+str(value)+']]></attribute>'+"\n")

    for file in node.getFiles():
        if file.type == "metadata":
            continue
        mimetype = file.mimetype
        if mimetype is None:
            mimetype = "application/x-download"
        fi.write((" "*indent) + '<file filename="'+esc(file.getName())+'" mime-type="'+mimetype+'" type="'+(file.type is not None and file.type or "image")+'"/>' + "\n")
    if children:
        for c in node.getChildren().sort():
            fi.write((" "*indent) + "<child id=\"%s\"/>\n" % str(c.id))
    indent -= 4
    fi.write((" "*indent) + '</node>'+"\n")
    if(children):
        for c in node.getChildren().sort():
            if c.id not in written:
                written[c.id] = None
                c.writexml(fi, indent)

class _StringWriter:
    def __init__(self):
        self.buffer = []
    def write(self,str):
        self.buffer.append(str)
    def get(self):
        return "".join(self.buffer)

def _writeNodeXML(node, fi):
    fi.write('<?xml version="1.0" encoding="utf-8"?>'+"\n")
    fi.write("<nodelist>\n")
    node.writexml(fi)
    fi.write("</nodelist>\n")

class _NodeLoader:

    def __init__(self,fi):
        self.root = None
        self.nodes = []
        self.attributename = None
        self.id2node = {}
        p = expat.ParserCreate()
        p.StartElementHandler = lambda name, attrs: self.xml_start_element(name,attrs)
        p.EndElementHandler = lambda name: self.xml_end_element(name)
        p.CharacterDataHandler = lambda d: self.xml_char_data(d)
        p.ParseFile(fi)
        fi.close()

        for node in self.nodes:
            for id in node.tmpchilds:
                child = self.id2node[id]
                node.addChild(child)

    def xml_start_element(self, name, attrs):
        try:
            node = self.nodes[-1]
        except:
            node = None
        if name == "node":
            parent = node
            try:
                type=attrs["type"].encode("utf-8")
            except:
                type="directory"
            
            node = tree.Node(name=attrs["name"].encode("utf-8"), type=type)
            
            if "read" in attrs:
                node.setAccess("read", attrs["read"].encode("utf-8"))
            if "write" in attrs:
                node.setAccess("write", attrs["write"].encode("utf-8"))
            if "data" in attrs:
                node.setAccess("data", attrs["data"].encode("utf-8"))

            if "id" not in attrs:
                attrs["id"] = str(random.random())
            self.id2node[attrs["id"].encode("utf-8")] = node
            node.tmpchilds = []
            self.nodes += [node]
            if self.root is None:
                self.root = node
            return
        elif name == "attribute":
            if "value" in attrs:
                node.setAttribute(attrs["name"].encode("utf-8"), attrs["value"].encode("utf-8"))
            else:
                self.attributename = attrs["name"].encode("utf-8")
        elif name == "child":
            id = u(attrs["id"])
            node.tmpchilds += [id]
        elif name == "file":
            try:
                type = attrs["type"].encode("utf-8")
            except:
                type = None

            try:
                mimetype = attrs["mime-type"].encode("utf-8")
            except:
                mimetype = None
            
            filename = attrs["filename"].encode("utf-8")

            node.addFile(tree.FileNode(name=filename, type=type, mimetype=mimetype))

    def xml_end_element(self, name):
        self.attributename = None

    def xml_char_data(self, data):
        if self.attributename:
            try:
                val = self.nodes[-1].get(self.attributename)
            except:
                val = ""
            self.nodes[-1].set(self.attributename, val+data.encode("utf-8"))

tree.registerNodeFunction("writexml", writexml)

def parseNodeXML(s):
    file = StringIO.StringIO(s)
    n = _NodeLoader(file)
    return n.root

def readNodeXML(filename):
    file = open(filename, "rb")
    n = _NodeLoader(file)
    return n.root

def writeNodeXML(node, filename):
    fi = open(filename, "wb")
    _writeNodeXML(node,fi)
    fi.close()

def getNodeXML(node):
    wr = _StringWriter()
    _writeNodeXML(node,wr)
    return wr.get()

def getSingleNodeXML(node):
    wr = _StringWriter()
    writexml(node,wr,children=False)
    return wr.get()
