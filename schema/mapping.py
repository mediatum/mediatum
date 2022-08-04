# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import core as _core
from core.database.postgres.node import Node
from core.xmlnode import getNodeXML, readNodeXML
from core.postgres import check_type_arg
import core.nodecache as _nodecache


def getMapping(nid):
    return _core.db.query(Node).get(nid) or _nodecache.get_mappings_node().getChild(nid)


def getMappingTypes():
    ret = []
    try:
        mappings = _nodecache.get_mappings_node()
        ret = mappings.get("mappingtypes").split(";")
        if len(ret) == 0 or ret[0] == "":
            mappings.set("mappingtypes", ";".join(("default", "bibtex", "rss", "marc21", "citeproc")))
            _core.db.session.commit()
            ret = getMappingTypes()
    except:
        pass
    return ret


def updateMapping(name, namespace="", namespaceurl="", description="", header="", footer="",
                  separator="", standardformat="", id=0, mappingtype="", active=""):
    if id != "" and int(id) > 0:
        mapping = _core.db.query(Node).get(id)
    else:
        mappings = _nodecache.get_mappings_node()
        mapping = Mapping(name=name)
        mappings.children.append(mapping)
    mapping.name = name
    mapping.setDescription(description)
    mapping.setNamespace(namespace)
    mapping.setNamespaceUrl(namespaceurl)
    mapping.setHeader(header)
    mapping.setFooter(footer)
    mapping.setSeparator(separator)
    mapping.setStandardFormat(standardformat)
    mapping.setMappingType(mappingtype)
    mapping.setActive(active)
    _core.db.session.commit()


def deleteMapping(name):
    mappings = _nodecache.get_mappings_node()
    mappings.children.remove(getMapping(name))
    _core.db.session.commit()


def updateMappingField(parentid, name, description="", exportformat="", mandatory=False, default="", id=0):
    mapping = _core.db.query(Node).get(parentid)
    if id != "" and int(id) > 0:
        mappingfield = _core.db.query(Node).get(id)
    else:
        mappingfield = MappingField(name=name)
        mapping.children.append(mappingfield)
    mappingfield.name = name
    mappingfield.setDescription(description)
    mappingfield.setExportFormat(exportformat)
    mappingfield.setMandatory(mandatory)
    mappingfield.setDefault(default)
    _core.db.session.commit()


def deleteMappingField(name):
    node = _core.db.query(Node).get(name)
    for p in node.parents:
        if p.type == "mapping":
            p.children.remove(node)
            _core.db.session.commit()
            return


def exportMapping(name):
    if name == "all":
        return getNodeXML(_nodecache.get_mappings_node())
    else:
        id = _core.db.query(Node).filter_by(name=unicode(name)).one().id
        return getNodeXML(getMapping(id))


def importMapping(filename):
    n = readNodeXML(filename)
    if n.getContentType() == "mapping":
        importlist = (n,)
    elif n.getContentType() == "mappings":
        importlist = tuple(n.children)
    else:
        importlist = ()

    mappings = _nodecache.get_mappings_node()
    for m in importlist:
        m.name = u"import-{}".format(m.getName())
        mappings.children.append(m)
    _core.db.session.commit()


@check_type_arg
class Mapping(Node):

    def getDescription(self):
        return self.get("description")

    def setDescription(self, description):
        self.set("description", description)

    def getNamespace(self):
        return self.get("namespace")

    def setNamespace(self, namespace):
        self.set("namespace", namespace)

    def getNamespaceUrl(self):
        return self.get("namespaceurl")

    def setNamespaceUrl(self, url):
        self.set("namespaceurl", url)

    def getHeader(self):
        return self.get("header")

    def setHeader(self, header):
        self.set("header", header)

    def getFooter(self):
        return self.get("footer")

    def setFooter(self, footer):
        self.set("footer", footer)

    def getSeparator(self):
        return self.get("separator")

    def setSeparator(self, separator):
        self.set("separator", separator)

    def getStandardFormat(self):
        return self.get("standardformat")

    def setStandardFormat(self, standardformat):
        self.set("standardformat", standardformat)

    def getFields(self):
        return sorted(self.children, key=lambda f: f.name.lower())

    def getMandatoryFields(self):
        return [f for f in self.getFields() if f.getMandatory()]

    def addField(self, field):
        self.children.append(field)

    def getFieldtype(self):
        return "mapping"

    def getActive(self):
        return int(self.get("active") != "0")

    def setActive(self, value):
        self.set("active", ustr("0" if value is None else value))

    def getMappingType(self):
        return self.get("mappingtype") or "default"

    def setMappingType(self, value):
        self.set("mappingtype", value)


@check_type_arg
class MappingField(Node):

    def getFullName(self):
        return u"{}{}".format(self.name, " *" if self.getMandatory() else "")

    def getDescription(self):
        return self.get("description")

    def setDescription(self, description):
        self.set("description", description)

    def getExportFormat(self):
        if self.get("exportformat"):
            return self.get("exportformat")
        mapping = self.getMapping()
        return mapping.getStandardFormat() if mapping else ""

    def setExportFormat(self, exportformat):
        self.set("exportformat", exportformat)

    def getMandatory(self):
        return self.get("mandatory") == "True"

    def setMandatory(self, mandatory):
        self.set("mandatory", "True" if mandatory else "False")

    def getMapping(self):
        return self.parents.filter_by(type=u"mapping").first()

    def getFieldtype(self):
        return "mappingfield"

    def getDefault(self):
        return self.get("default")

    def setDefault(self, value):
        self.set('default', value)
