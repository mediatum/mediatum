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
import logging
import codecs

from utils.utils import esc, u, u2

import core.users as users
from core.acl import AccessData

EXCLUDE_WORKFLOW_NEWNODES = True


logg = logging.getLogger(__name__)


def getInformation():
    return {"version": "1.1a", "system": 1}


def writexml(node, fi, indent=None, written=None, children=True, children_access=None,
             exclude_filetypes=[], exclude_children_types=[], attribute_name_filter=None):
    if written is None:
        written = {}
    if indent is None:
        indent = 0
    # there are a lot of nodes without name ...
    nodename_copy = node.name
    if nodename_copy is None:
        nodename_copy = ""
    #fi.write('%s<node name="%s" id="%s" ' % ((" " * indent), esc(nodename_copy), ustr(node.id)))
    # non-utf8 encoded umlauts etc. may cause invalid xml
    fi.write('%s<node name="%s" id="%s" ' % ((" " * indent), u2(esc(nodename_copy)), ustr(node.id)))
    if node.type is None:
        node.type = "node"
    fi.write('type="%s" ' % node.type)
    if node.read_access:
        fi.write('read="%s" ' % esc(node.read_access))
    if node.write_access:
        fi.write('write="%s" ' % esc(node.write_access))
    if node.data_access:
        fi.write('data="%s" ' % esc(node.data_access))
    fi.write(">\n")

    indent += 4

    for name, value in node.items():
        u_esc_name = u(esc(name))
        if attribute_name_filter and not attribute_name_filter(u_esc_name):
            continue
        fi.write('%s<attribute name="%s"><![CDATA[%s]]></attribute>\n' % ((" " * indent), u_esc_name, u2(value)))

    for file in node.getFiles():
        if file.type == "metadata" or file.type in exclude_filetypes:
            continue
        mimetype = file.mimetype
        if mimetype is None:
            mimetype = "application/x-download"
        fi.write('%s<file filename="%s" mime-type="%s" type="%s"/>\n' %
                 ((" " * indent), esc(file.getName()), mimetype, (file.type is not None and file.type or "image")))
    if children:
        for c in node.getChildren().sort_by_orderpos():
            if (not children_access) or (children_access and children_access.hasAccess(c, 'read')):
                if c.type not in exclude_children_types:
                    fi.write('%s<child id="%s" type="%s"/>\n' % ((" " * indent), ustr(c.id), c.type))

    indent -= 4
    fi.write("%s</node>\n" % (" " * indent))
    if(children):
        for c in node.getChildren().sort_by_orderpos():
            if (not children_access) or (children_access and children_access.hasAccess(c, 'read')):
                if c.type not in exclude_children_types:
                    if c.id not in written:
                        written[c.id] = None
                        c.writexml(fi, indent=indent,
                                   written=written,
                                   children=children,
                                   children_access=children_access,
                                   exclude_filetypes=exclude_filetypes,
                                   exclude_children_types=exclude_children_types,
                                   attribute_name_filter=attribute_name_filter
                                   )

    if node.type in ["mask"]:
        try:
            exportmapping_id = node.get("exportmapping").strip()
            if exportmapping_id and exportmapping_id not in written:
                try:
                    exportmapping = tree.getNode(exportmapping_id)
                    written[exportmapping_id] = None
                    exportmapping.writexml(fi, indent=indent,
                                           written=written,
                                           children=children,
                                           children_access=children_access,
                                           exclude_filetypes=exclude_filetypes,
                                           exclude_children_types=exclude_children_types,
                                           attribute_name_filter=attribute_name_filter
                                           )
                except:
                    logg.exception("ERROR: node xml export error node.id='%s', node.name='%s', node.type='%s', exportmapping:'%s'",
                        node.id, node.name, node.type, exportmapping_id)
            else:
                pass
        except:
            logg.exception("ERROR: node xml export error node.id='%s', node.name='%s', node.type='%s', exportmapping:'%s'",
                           node.id, node.name, node.type, exportmapping_id)


class _StringWriter:

    def __init__(self):
        self.buffer = []

    def write(self, ustr):
        self.buffer.append(ustr)

    def get(self):
        return "".join(self.buffer)


def _writeNodeXML(node, fi):
    fi.write('<?xml version="1.0" encoding="utf-8"?>' + "\n")
    fi.write('<nodelist exportversion="%s" rootname="%s" roottype="%s" original_nodeid="%s">\n' %
             (getInformation()["version"], node.name, node.type, ustr(node.id)))
    exclude_children_types = []
    if EXCLUDE_WORKFLOW_NEWNODES and node.type == 'workflow':
        for c in node.getChildren():
            if c.type == "workflowstep-start":
                newnodetypes = c.get("newnodetype").strip().split(";")
                for newnodetype in newnodetypes:
                    exclude_children_types.append(newnodetype)
    node.writexml(fi, exclude_children_types=exclude_children_types)
    fi.write("</nodelist>\n")


class _NodeLoader:

    def __init__(self, fi, verbose=True):
        self.root = None
        self.nodes = []
        self.attributename = None
        self.id2node = {}
        self.verbose = verbose
        self.node_already_seen = False
        p = expat.ParserCreate()
        p.StartElementHandler = lambda name, attrs: self.xml_start_element(name, attrs)
        p.EndElementHandler = lambda name: self.xml_end_element(name)
        p.CharacterDataHandler = lambda d: self.xml_char_data(d)
        try:
            p.ParseFile(fi)
        except expat.ExpatError as e:
            logg.exception("\tfile not well-formed in line %s, %s", e.lineno, e.offset)
            return
        finally:
            fi.close()

        try:
            mappings = tree.getRoot("mappings")
        except tree.NoSuchNodeError:
            mappings = tree.getRoot().addChild(tree.Node(name="mappings", type="mappings"))
            logg.info("no mappings root found: added mappings root")

        for node in self.nodes:
            if node.type == "mapping":
                if node.name not in [n.name for n in mappings.getChildren() if n.type == "mapping"]:
                    mappings.addChild(node)
                    if self.verbose:
                        logg.info("xml import: added  mapping id=%s, type='%s', name='%s'", node.id, node.type, node.name)

        if self.verbose:
            logg.info("linking children to parents")
        for node in self.nodes:
            d = {}
            for id in node.tmpchilds:
                child = self.id2node[id]
                node.addChild(child)
                d[child.id] = child
            if self.verbose and node.tmpchilds:
                added = [(cid, d[cid].type, d[cid].name) for cid in d.keys()]
                logg.info("added %d children to node id='%s', type='%s', name='%s': %s",
                    len(node.tmpchilds), node.id, node.type, node.name, added)

        for node in self.nodes:
            if node.type == "maskitem":
                attr = node.get("attribute")
                if attr and attr in self.id2node:
                    attr_new = self.id2node[attr].id
                    node.set("attribute", attr_new)
                    if self.verbose:
                        logg.info("adjusting node attribute for maskitem '%s', name='attribute', value: old='%s' -> new='%s'",
                            node.id, attr, attr_new)
                mappingfield = node.get("mappingfield")
                if mappingfield and mappingfield in self.id2node:
                    mappingfield_new = self.id2node[mappingfield].id
                    node.set("mappingfield", ustr(mappingfield_new))
                    if self.verbose:
                        logg.info("adjusting node attribute for maskitem '%s', name='mappingfield', value old='%s' -> new='%s'",
                            node.id, mappingfield, mappingfield_new)
            elif node.type == "mask":
                exportmapping = node.get("exportmapping")
                if exportmapping and exportmapping in self.id2node:
                    exportmapping_new = self.id2node[exportmapping].id
                    node.set("exportmapping", ustr(exportmapping_new))
                    if self.verbose:
                        logg.info("adjusting node attribute for mask '%s',  name='exportmapping':, value old='%s' -> new='%s'",
                            node.id, exportmapping, exportmapping_new)

        logg.info("xml import done")

    def xml_start_element(self, name, attrs):
        try:
            node = self.nodes[-1]
        except:
            node = None
        if name == "nodelist":
            if "exportversion" in attrs:
                logg.info("starting xml import: %s", attrs)

        elif name == "node":
            self.node_already_seen = False
            parent = node
            try:
                type = attrs["type"].encode("utf-8")
            except:
                type = "directory"

            if "id" not in attrs:
                attrs["id"] = ustr(random.random())

            old_id = attrs["id"]

            if old_id in self.id2node:
                node = self.id2node[old_id]
                self.node_already_seen = True
                return
            elif type in ["mapping"]:
                node = tree.Node(name=(attrs["name"] + "_imported_" + old_id).encode("utf-8"), type=type)
            else:
                node = tree.Node(name=attrs["name"].encode("utf-8"), type=type)

            if "read" in attrs:
                node.setAccess("read", attrs["read"].encode("utf-8"))
            if "write" in attrs:
                node.setAccess("write", attrs["write"].encode("utf-8"))
            if "data" in attrs:
                node.setAccess("data", attrs["data"].encode("utf-8"))

            if self.verbose:
                logg.info("created node '%s', '%s', '%s', old_id from attr='%s'", node.name, node.type, node.id, attrs["id"])

            self.id2node[attrs["id"].encode("utf-8")] = node
            node.tmpchilds = []
            self.nodes += [node]
            if self.root is None:
                self.root = node
            return
        elif name == "attribute" and not self.node_already_seen:
            attr_name = attrs["name"].encode("utf-8")
            if "value" in attrs:
                if attr_name in ["valuelist"]:
                    node.setAttribute(attr_name, attrs["value"].encode("utf-8").replace("\n\n", "\n").replace("\n", ";").replace(";;", ";"))
                else:
                    node.setAttribute(attr_name, attrs["value"].encode("utf-8"))
            else:
                self.attributename = attr_name

        elif name == "child" and not self.node_already_seen:
            id = u(attrs["id"])
            node.tmpchilds += [id]
        elif name == "file" and not self.node_already_seen:
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
        if self.node_already_seen:
            return
        if name == "node":
            pass
        elif name == "attribute":
            if self.verbose:
                logg.info("  -> : added attribute '%s': '%s'", self.attributename, self.nodes[-1].get(self.attributename))
        self.attributename = None

    def xml_char_data(self, data):
        if self.node_already_seen:
            return
        if self.attributename:
            try:
                val = self.nodes[-1].get(self.attributename)
                n = self.nodes[-1]
            except:
                val = ""
            if self.attributename in ["valuelist"]:
                self.nodes[-1].set(self.attributename,
                                   (val + data.encode("utf-8")).replace("\n\n", "\n").replace("\n", ";").replace(";;", ";"))
            else:
                self.nodes[-1].set(self.attributename, val + data.encode("utf-8"))

tree.registerNodeFunction("writexml", writexml)


def parseNodeXML(s):
    return _NodeLoader(StringIO.StringIO(s)).root


def readNodeXML(filename):
    try:
        return _NodeLoader(codecs.open(filename, "rb", encoding='utf8')).root
    except IOError:
        return None


def writeNodeXML(node, filename):
    with codecs.open(filename, "wb") as fi:
        _writeNodeXML(node, fi)

def getNodeXML(node):
    wr = _StringWriter()
    _writeNodeXML(node, wr)
    return wr.get()


def getNodeListXMLForUser(node, readuser=None, exclude_filetypes=[], attribute_name_filter=None):
    if readuser:
        # only write child data if children_access_user has read access
        children_access = AccessData(user=users.getUser(readuser))
    else:
        children_access = None
    wr = _StringWriter()
    wr.write('<nodelist exportversion="%s">\n' % getInformation()["version"])
    node.writexml(wr, children_access=children_access, exclude_filetypes=exclude_filetypes, attribute_name_filter=attribute_name_filter)
    wr.write("</nodelist>\n")
    return wr.get()


def getSingleNodeXML(node, exclude_filetypes=[], attribute_name_filter=None):
    wr = _StringWriter()
    writexml(node, wr, children=False, exclude_filetypes=exclude_filetypes, attribute_name_filter=attribute_name_filter)
    return wr.get()
