# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from core.database.postgres.node import Node
import itertools as _itertools
import logging
import operator as _operator

import sqlalchemy as _sqlalchemy

import werkzeug.datastructures as _werkzeug_datastructures
from lxml import etree

import core as _core
import core.nodecache as _core_nodecache
import utils.utils as _utils_utils
from core.database.postgres.file import File

EXCLUDE_WORKFLOW_NEWNODES = True

logg = logging.getLogger(__name__)


def create_xml_nodelist(xmlroot=None):
    if xmlroot is None:
        xmlnodelist = etree.Element("nodelist")
    else:
        xmlnodelist = etree.SubElement(xmlroot, "nodelist")

    return xmlnodelist


def add_node_to_xmldoc(
        node,
        xmlroot,
        children=True,
        exclude_filetypes=frozenset(),
        exclude_childtypes=frozenset(),
        attribute_name_filter=lambda name:True,
        _written=None,
       ):

    from schema.schema import Mask
    from schema.mapping import Mapping

    if _written is None:
        _written = set()

    _written.add(node.id)

    xmlnode = etree.SubElement(xmlroot, "node")
    xmlnode.set("name", node.name or u"")
    xmlnode.set("id", unicode(node.id))
    xmlnode.set("type", (node.type + "/" + (node.schema or u"")).strip("/"))
    xmlnode.set("datatype", node.type)
    xmlnode.set("schema", (node.schema or u""))

    for name in sorted(filter(attribute_name_filter, node.attrs)):
        xmlattr = etree.SubElement(xmlnode, "attribute")
        xmlattr.set("name", name)
        xmlattr.text = _utils_utils.xml_remove_illegal_chars(unicode(node.attrs[name]))

    exclude_filetypes = set(exclude_filetypes)
    exclude_filetypes.add(u"metadata")
    for fileobj in node.file_objects:
        if fileobj.filetype not in exclude_filetypes:
            etree.SubElement(xmlnode, "file").attrib.update({
                "filename": fileobj.base_name,
                "mime-type": fileobj.mimetype,
                "type": fileobj.filetype
               })

    if children:
        child_query = node.children

        if exclude_childtypes:
            child_query = child_query.filter(_sqlalchemy.or_(Node.schema == None, ~((Node.type + u'/' + Node.schema).in_(exclude_childtypes))))

        for child in child_query.order_by("orderpos"):
            etree.SubElement(xmlnode, "child").attrib.update(dict(
                id=unicode(child.id),
                type=u"{}/{}".format(child.type,child.schema) if child.schema else child.type,
                datatype=child.type,
                schema=(child.schema or u""),
               ))

            if child.id not in _written:
                add_node_to_xmldoc(child, xmlroot, children, exclude_filetypes, exclude_childtypes, attribute_name_filter, _written)

    if isinstance(node, Mask):
        exportmappings = node.get(u"exportmapping").split(";")
        exportmappings = _itertools.imap(_operator.methodcaller("strip"), exportmappings)
        exportmappings = _itertools.ifilter(None, exportmappings)
        exportmappings = _itertools.imap(int, exportmappings)
        exportmappings = set(exportmappings)
        exportmappings.difference_update(_written)
        exportmappings = _itertools.imap(_core.db.query(Mapping).get, exportmappings)
        exportmappings = _itertools.ifilter(None, exportmappings)
        for mapping in exportmappings:
            add_node_to_xmldoc(mapping, xmlroot, children, exclude_filetypes, exclude_childtypes, attribute_name_filter=attribute_name_filter, _written=_written)
    return xmlnode


class _NodeLoaderTarget(object):

    def __init__(self):
        self.root = None
        self.nodes = []
        self._attributename = None
        self.id2node = {}
        self._node_already_seen = False
        self._rand =_utils_utils.gen_secure_token(128)

    def start(self, name, attrs):
        node = None
        with _utils_utils.suppress(Exception):
            node = self.nodes[-1]
        if name == "nodelist":
            logg.debug("xml node import: found <nodelist>, proceeding with import")

        elif name == "node":
            self._node_already_seen = False
            parent = node

            # compatibility for old xml files created with mediatum:
            # old files use "type", new files use "datatype"
            datatype = attrs.get("datatype", attrs.get("type", "directory"))

            old_id = attrs.setdefault("id", _utils_utils.gen_secure_token(128))
            assert old_id

            if old_id in self.id2node:
                node = self.id2node[old_id]
                self._node_already_seen = True
                return

            content_class = Node.get_class_for_typestring(datatype)
            if datatype=="mapping":
                node = content_class(name=u"{}_import_{}".format(attrs["name"], self._rand))
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
                _core.db.session.commit()
            return

        if self._node_already_seen:
            return

        if name == "attribute":
            attr_name = attrs["name"]
            if "value" not in attrs:
                self._attributename = attr_name
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

    def end(self, name):
        if not self._node_already_seen:
            if name == "attribute":
                logg.debug(
                        "xml import: "
                        "added attribute '%s': '%s'",
                        self._attributename, self.nodes[-1].get(self._attributename),
                       )
            self._attributename = None

    def data(self, data):
        if self._node_already_seen or not self._attributename:
            return
        val = ""
        with _utils_utils.suppress(Exception):
            val = self.nodes[-1].get(self._attributename)
            n = self.nodes[-1]
        val += data
        if self._attributename=="valuelist":
            val = val.replace("\n\n", "\n").replace("\n", ";").replace(";;", ";")
        self.nodes[-1].set(self._attributename, val)

    def comment(self, text):
        pass

    def close(self):
        return "closed!"


def readNodeXML(fi):
    if type(fi) in (unicode, str):
        xml = fi
    elif type(fi) in (file, _werkzeug_datastructures.FileStorage):
        xml = fi.read()
        fi.close()
    else:
        raise NotImplementedError()
    nodeloader = _NodeLoaderTarget()
    xmlparser = etree.XMLParser(target=nodeloader)
    try:
        etree.XML(xml, xmlparser)
    except:
        logg.exception("failed to parse XML, maybe invalid content")
        return
    mappings = _core_nodecache.get_mappings_node()
    for node in nodeloader.nodes:
        if (node.type == "mapping") and not any(node.name == n.name for n in mappings.children if n.type == "mapping"):
            mappings.children.append(node)
            _core.db.session.commit()
            logg.debug("xml import: added  mapping id=%s, type='%s', name='%s'", node.id, node.type, node.name)

    logg.debug("xml import: linking children to parents")
    for node in nodeloader.nodes:
        node.children.extend(nodeloader.id2node[i] for i in node.tmpchilds)
        logg.debug("xml import: added %d children to node id='%s', type='%s', name='%s'",
                len(node.tmpchilds), node.id, node.type, node.name)
    _core.db.session.commit()

    for node in nodeloader.nodes:
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
            if attr in nodeloader.id2node:
                logg.debug(
                        "xml import: "
                        "adjusting node attribute '%s' for %s: %s -> %s",
                        attr_name, node.type, attr, ustr(nodeloader.id2node[attr].id)
                       )
                node.set(attr_name, ustr(nodeloader.id2node[attr].id))

    logg.info("xml import done")
    _core.db.session.commit()
    return nodeloader.root


def getNodeXML(node):
    nodelist = create_xml_nodelist()

    nodelist.set('rootname', node.name)
    nodelist.set('roottype', (node.type + "/" + (node.schema or u"")).strip("/"))
    nodelist.set('rootdatatype', node.type)
    nodelist.set('rootschema', (node.schema or u""))
    nodelist.set('original_nodeid', unicode(node.id))

    from workflow.workflow import Workflow
    exclude_childtypes = set()
    if EXCLUDE_WORKFLOW_NEWNODES and isinstance(node, Workflow):
        for c in node.children:
            if c.type == "workflowstep_start":
                exclude_childtypes.update(c.get("newnodetype").strip().split(";"))

    add_node_to_xmldoc(node, nodelist, exclude_childtypes=exclude_childtypes)
    return etree.tostring(nodelist, xml_declaration=True, pretty_print=True, encoding="utf8")
