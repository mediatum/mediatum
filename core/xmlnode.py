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
from core import Node
import random
import logging

from lxml import etree
from core import File, db
from core.systemtypes import Mappings, Root
from utils.compat import iteritems
from utils.xml import xml_remove_illegal_chars
from utils.list import filter_scalar


EXCLUDE_WORKFLOW_NEWNODES = True

q = db.query
logg = logging.getLogger(__name__)

EXPORTVERSION = u"1.1a"


def create_xml_nodelist(xmlroot=None):
    if xmlroot is None:
        xmlnodelist = etree.Element("nodelist")
    else:
        xmlnodelist = etree.SubElement(xmlroot, "nodelist")

    xmlnodelist.set("exportversion", EXPORTVERSION)
    return xmlnodelist


def add_file_to_xmlnode(file, xmlnode):
    xmlfile = etree.SubElement(xmlnode, "file")
    xmlfile.set("filename", file.base_name)
    xmlfile.set("mime-type", file.mimetype)
    xmlfile.set("type", file.filetype)


def add_child_to_xmlnode(child, xmlnode):
    xmlchild = etree.SubElement(xmlnode, "child")
    xmlchild.set("id", unicode(child.id))
    xmlchild.set("type", (child.type + "/" + (child.schema or u"")).strip("/"))
    xmlchild.set("datatype", child.type)
    xmlchild.set("schema", (child.schema or u""))


def add_node_to_xmldoc(
        node,
        xmlroot,
        written=set(),
        children=True,
        exclude_filetypes=[],
        exclude_childtypes=[],
        attribute_name_filter=None):

    from schema.schema import Mask
    from schema.mapping import Mapping

    written.add(node.id)

    xmlnode = etree.SubElement(xmlroot, "node")
    xmlnode.set("name", node.name or u"")
    xmlnode.set("id", unicode(node.id))
    xmlnode.set("type", (node.type + "/" + (node.schema or u"")).strip("/"))
    xmlnode.set("datatype", node.type)
    xmlnode.set("schema", (node.schema or u""))

    # TODO: no access rights at the moment

    for name, value in sorted(iteritems(node.attrs)):
        if attribute_name_filter and not attribute_name_filter(name):
            continue
        xmlattr = etree.SubElement(xmlnode, "attribute")
        xmlattr.set("name", name)
        # protect XML from invalid characters
        # XXX: is this ok?
        xmlattr.text = etree.CDATA(xml_remove_illegal_chars(unicode(value)))

    files = [f for f in node.file_objects if f.filetype != u"metadata"]
 
    if exclude_filetypes:
        files = [f for f in files if f.filetype not in (exclude_filetypes)]

    for fileobj in files:
        add_file_to_xmlnode(fileobj, xmlnode)

    if children:
        child_query = node.children

        if exclude_childtypes:
            child_query = child_query.filter(~Node.type.in_(exclude_childtypes))

        for child in child_query.order_by("orderpos"):
            add_child_to_xmlnode(child, xmlnode)

            if child.id not in written:
                add_node_to_xmldoc(child, xmlroot, written, children, exclude_filetypes, exclude_childtypes, attribute_name_filter)

    if isinstance(node, Mask):
        exportmapping_id = node.get(u"exportmapping").strip()
        if exportmapping_id and exportmapping_id not in written:
            mapping = q(Mapping).get(int(exportmapping_id))
            if mapping is not None:
                written.add(mapping.id)
                add_node_to_xmldoc(mapping, xmlroot, written, children, exclude_filetypes, exclude_childtypes, attribute_name_filter)
    return xmlnode


class HandlerTarget(object):
    def start(self, tag, attrib):
        logg.info("default handler start %s %r" % (tag, dict(attrib)))
    def end(self, tag):
        logg.info("default handler end %s" % tag)
    def data(self, data):
        logg.info("default handler data %r" % data)
    def comment(self, text):
        logg.info("default handler comment %s" % text)
    def close(self):
        logg.info("default handler close")
        return "closed!"


class _NodeLoader:

    def __init__(self, fi, verbose=True):
        self.root = None
        self.nodes = []
        self.attributename = None
        self.id2node = {}
        self.verbose = verbose
        self.node_already_seen = False

        handler = HandlerTarget()
        handler.start = lambda name, attrs: self.xml_start_element(name, attrs)
        handler.end = lambda name: self.xml_end_element(name)
        handler.data = lambda d: self.xml_char_data(d)

        parser = etree.XMLParser(target = handler)
        if type(fi) in [unicode, str]:
            xml = fi
        elif type(fi) in [file]:
            xml = fi.read()
            fi.close()
        else:
            raise NotImplementedError()
        try:
            result = etree.XML(xml, parser)
        except Exception as e:
            logg.exception("\tfile not well-formed. %s", e)
            return

        mappings = q(Mappings).scalar()
        if mappings is None:
            mappings = q(Root).one().children.append(Node(name="mappings", type="mappings"))
            logg.info("no mappings root found: added mappings root")

        for node in self.nodes:
            if node.type == "mapping":
                if node.name not in [n.name for n in mappings.children if n.type == "mapping"]:
                    mappings.children.append(node)
                    db.session.commit()
                    if self.verbose:
                        logg.info("xml import: added  mapping id=%s, type='%s', name='%s'", node.id, node.type, node.name)

        if self.verbose:
            logg.info("linking children to parents")
        for node in self.nodes:
            d = {}
            for id in node.tmpchilds:
                child = self.id2node[id]
                node.children.append(child)
                db.session.commit()
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
                    db.session.commit()
                    if self.verbose:
                        logg.info("adjusting node attribute for maskitem '%s', name='attribute', value: old='%s' -> new='%s'",
                                  node.id, attr, attr_new)
                mappingfield = node.get("mappingfield")
                if mappingfield and mappingfield in self.id2node:
                    mappingfield_new = self.id2node[mappingfield].id
                    node.set("mappingfield", ustr(mappingfield_new))
                    db.session.commit()
                    if self.verbose:
                        logg.info("adjusting node attribute for maskitem '%s', name='mappingfield', value old='%s' -> new='%s'",
                                  node.id, mappingfield, mappingfield_new)
            elif node.type == "mask":
                exportmapping = node.get("exportmapping")
                if exportmapping and exportmapping in self.id2node:
                    exportmapping_new = self.id2node[exportmapping].id
                    node.set("exportmapping", ustr(exportmapping_new))
                    db.session.commit()
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
                datatype = attrs["datatype"]
            except KeyError:
                # compatibility for old xml files created with mediatum
                t = attrs.get("type")
                if t is not None:
                    datatype = t
                else:
                    datatype = "directory"

            if "id" not in attrs:
                attrs["id"] = ustr(random.random())

            old_id = attrs["id"]

            if old_id in self.id2node:
                node = self.id2node[old_id]
                self.node_already_seen = True
                return
            elif datatype in ["mapping"]:
                content_class = Node.get_class_for_typestring(datatype)
                node = content_class(name=(attrs["name"] + "_imported_" + old_id))
            else:
                content_class = Node.get_class_for_typestring(datatype)
                node = content_class(name=attrs["name"])
            db.session.add(node)

            # todo: handle access

            #if "read" in attrs:
            #    node.setAccess("read", attrs["read"].encode("utf-8"))
            #if "write" in attrs:
            #    node.setAccess("write", attrs["write"].encode("utf-8"))
            #if "data" in attrs:
            #    node.setAccess("data", attrs["data"].encode("utf-8"))

            if self.verbose:
                logg.info("created node '%s', '%s', '%s', old_id from attr='%s'", node.name, node.type, node.id, attrs["id"])

            self.id2node[attrs["id"]] = node
            node.tmpchilds = []
            self.nodes.append(node)
            if self.root is None:
                self.root = node
            return
        elif name == "attribute" and not self.node_already_seen:
            attr_name = attrs["name"]
            if "value" in attrs:
                if attr_name in ["valuelist"]:
                    node.set(attr_name, attrs["value"].replace("\n\n", "\n").replace("\n", ";").replace(";;", ";"))
                else:
                    node.set(attr_name, attrs["value"])
            else:
                self.attributename = attr_name
            db.session.commit()

        elif name == "child" and not self.node_already_seen:
            nid = attrs["id"]
            node.tmpchilds += [nid]
        elif name == "file" and not self.node_already_seen:
            try:
                datatype = attrs["type"]
            except:
                datatype = None

            try:
                mimetype = attrs["mime-type"]
            except:
                mimetype = None

            filename = attrs["filename"]
            node.files.append(File(path=filename, filetype=datatype, mimetype=mimetype))
            db.session.commit()

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
                                   (val + data).replace("\n\n", "\n").replace("\n", ";").replace(";;", ";"))
            else:
                self.nodes[-1].set(self.attributename, val + data)
        db.session.commit()



def readNodeXML(filename):
    try:
        return _NodeLoader(open(filename, "rb")).root
    except IOError:
        return None


def getNodeXML(
        node,
        children=True,
        exclude_filetypes=[],
        exclude_childtypes=[],
        attribute_name_filter=None):

    nodelist = create_xml_nodelist()

    nodelist.set('rootname', node.name)
    nodelist.set('roottype', (node.type + "/" + (node.schema or u"")).strip("/"))
    nodelist.set('rootdatatype', node.type)
    nodelist.set('rootschema', (node.schema or u""))
    nodelist.set('original_nodeid', unicode(node.id))

    from workflow.workflow import Workflow
    if EXCLUDE_WORKFLOW_NEWNODES and isinstance(node, Workflow):
        for c in node.children:
            if c.type == "workflowstep_start":
                newnodetypes = c.get("newnodetype").strip().split(";")
                for newnodetype in newnodetypes:
                    if newnodetype not in exclude_childtypes:
                        exclude_childtypes.append(newnodetype)

    written = set()
    add_node_to_xmldoc(
        node,
        nodelist,
        written=written,
        children=children,
        exclude_filetypes=exclude_filetypes,
        exclude_childtypes=exclude_childtypes,
        attribute_name_filter=attribute_name_filter)

    xmlstr = etree.tostring(nodelist, xml_declaration=True, pretty_print=True, encoding="utf8")
    return xmlstr
