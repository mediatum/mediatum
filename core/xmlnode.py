# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from core import Node
import logging

import sqlalchemy as _sqlalchemy

import werkzeug.datastructures as _werkzeug_datastructures
from lxml import etree

import core.nodecache as _core_nodecache
import utils.utils as _utils_utils
from core import File, db
from utils.compat import iteritems
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
        xmlattr.text = etree.CDATA(_utils_utils.xml_remove_illegal_chars(unicode(value)))

    files = [f for f in node.file_objects if f.filetype != u"metadata"]
 
    if exclude_filetypes:
        files = [f for f in files if f.filetype not in (exclude_filetypes)]

    for fileobj in files:
        add_file_to_xmlnode(fileobj, xmlnode)

    if children:
        child_query = node.children

        if exclude_childtypes:
            child_query = child_query.filter(_sqlalchemy.or_(Node.schema == None, ~((Node.type + u'/' + Node.schema).in_(exclude_childtypes))))

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


class _HandlerTarget(object):
    def start(self, tag, attrib):
        raise NotImplementedError
    def end(self, tag):
        raise NotImplementedError
    def data(self, data):
        raise NotImplementedError
    def comment(self, text):
        pass
    def close(self):
        return "closed!"


class _NodeLoader(object):

    def __init__(self, xml):
        self.root = None
        self.nodes = []
        self.attributename = None
        self.id2node = {}
        self.node_already_seen = False
        self.rand =_utils_utils.gen_secure_token(128)

        handler = _HandlerTarget()
        handler.start = lambda name, attrs: self.xml_start_element(name, attrs)
        handler.end = lambda name: self.xml_end_element(name)
        handler.data = lambda d: self.xml_char_data(d)
        parser = etree.XMLParser(target = handler)

        try:
            result = etree.XML(xml, parser)
        except:
            logg.exception("xml import: xml file not well-formed.")
            return

        mappings = _core_nodecache.get_mappings_node()
        for node in self.nodes:
            if (node.type == "mapping") and not any(node.name == n.name for n in mappings.children if n.type == "mapping"):
                mappings.children.append(node)
                db.session.commit()
                logg.debug("xml import: added  mapping id=%s, type='%s', name='%s'", node.id, node.type, node.name)

        logg.debug("xml import: linking children to parents")
        for node in self.nodes:
            node.children.extend(self.id2node[i] for i in node.tmpchilds)
            logg.debug("xml import: added %d children to node id='%s', type='%s', name='%s'",
                    len(node.tmpchilds), node.id, node.type, node.name)
        db.session.commit()

        for node in self.nodes:
            if node.type == "maskitem":
                attrs_to_map = ["attribute"]
                if node.get("fieldtype") == u"mapping":
                    attrs_to_map.append("mappingfield")
            elif node.type == "mask":
                attrs_to_map = ("exportmapping", )
            else:
                attrs_to_map = ()
            for attr_name in attrs_to_map:
                attr = node.get(attr_name)
                if attr in self.id2node:
                    logg.debug(
                            "xml import: "
                            "adjusting node attribute '%s' for %s: %s -> %s",
                            attr_name, node.type, attr, ustr(self.id2node[attr].id)
                           )
                    node.set(attr_name, ustr(self.id2node[attr].id))

        logg.info("xml import done")
        db.session.commit()

    def xml_start_element(self, name, attrs):
        node = None
        with _utils_utils.suppress(Exception):
            node = self.nodes[-1]
        if name == "nodelist":
            if "exportversion" in attrs:
                logg.info("starting xml import: %s", attrs)

        elif name == "node":
            self.node_already_seen = False
            parent = node

            # compatibility for old xml files created with mediatum:
            # old files use "type", new files use "datatype"
            datatype = attrs.get("datatype", attrs.get("type", "directory"))

            old_id = attrs.setdefault("id", _utils_utils.gen_secure_token(128))
            assert old_id

            if old_id in self.id2node:
                node = self.id2node[old_id]
                self.node_already_seen = True
                return

            content_class = Node.get_class_for_typestring(datatype)
            if datatype=="mapping":
                node = content_class(name=u"{}_import_{}".format(attrs["name"], self.rand))
            else:
                node = content_class(name=attrs["name"])

            logg.debug(
                    "xml import: "
                    "created node '%s', '%s', '%s', "
                    "old_id from attr='%s'",
                    node.name, node.type, node.id, attrs["id"],
                   )

            self.id2node[attrs["id"]] = node
            node.tmpchilds = []
            self.nodes.append(node)
            if self.root is None:
                self.root = node
                # temporarly add self.root to 'root' to get an node.id for self.root
                # so all children of self.root gets a node.id after db.session.commit()
                # this is neccessary to get a node.id for the attribute 'attribute' for maskitems of exportmasks
                root = _core_nodecache.get_root_node()
                root.children.append(self.root)
                root.children.remove(self.root)
                db.session.commit()
            return

        if self.node_already_seen:
            return

        if name == "attribute":
            attr_name = attrs["name"]
            if "value" not in attrs:
                self.attributename = attr_name
                return
            attr_value = attrs["value"]
            if attr_name=="valuelist":
                attr_value = attr_value.replace("\n\n", "\n").replace("\n", ";").replace(";;", ";")
            node.set(attr_name, attr_value)

        elif name == "child":
            node.tmpchilds.append(attrs["id"])
        elif name == "file":
            # note: this likely doesn't work if export/import
            # is done on different mediatum installations
            node.files.append(File(
                    path=attrs["filename"],
                    filetype=attrs.get("type"),
                    mimetype=attrs.get("mime-type"),
                   ))

    def xml_end_element(self, name):
        if not self.node_already_seen:
            if name == "attribute":
                logg.debug(
                        "xml import: "
                        "added attribute '%s': '%s'",
                        self.attributename, self.nodes[-1].get(self.attributename),
                       )
            self.attributename = None

    def xml_char_data(self, data):
        if self.node_already_seen or not self.attributename:
            return
        val = ""
        with _utils_utils.suppress(Exception):
            val = self.nodes[-1].get(self.attributename)
            n = self.nodes[-1]
        val += data
        if self.attributename=="valuelist":
            val = val.replace("\n\n", "\n").replace("\n", ";").replace(";;", ";")
        self.nodes[-1].set(self.attributename, val)



def readNodeXML(fi):
    if type(fi) in (unicode, str):
        xml = fi
    elif type(fi) in (file, _werkzeug_datastructures.FileStorage):
        xml = fi.read()
        fi.close()
    else:
        raise NotImplementedError()
    return _NodeLoader(xml).root


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
