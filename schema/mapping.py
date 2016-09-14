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
from core.xmlnode import getNodeXML, readNodeXML
from core.transition.postgres import check_type_arg

from core import db
from core.systemtypes import Mappings, Root

q = db.query


def getMappings():
    mappings = q(Mappings).scalar()
    if mappings is None:
        root = q(Root).one()
        root.children.append(Mappings(u"mappings"))
        mappings = q(Mappings).one()
        db.session.commit()

    try:
        return mappings.children
    except:
        return []


def getMapping(id):
    n = q(Node).get(id)
    if n is None:
        mappings = q(Mappings).one()
        return mappings.getChild(id)
    return n


def getMappingTypes():
    ret = []
    try:
        mappings = q(Mappings).one()
        ret = mappings.get("mappingtypes").split(";")
        if len(ret) == 0 or ret[0] == "":
            mappings.set("mappingtypes", "default;bibtex;rss;marc21;z3950;citeproc")
            db.session.commit()
            return getMappingTypes()
        return ret
    except:
        return ret


def updateMapping(name, namespace="", namespaceurl="", description="", header="", footer="",
                  separator="", standardformat="", id=0, mappingtype="", active=""):
    if id != "" and int(id) > 0:
        mapping = q(Node).get(id)
    else:
        mappings = q(Mappings).one()
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
    db.session.commit()


def deleteMapping(name):
    mappings = q(Mappings).one()
    mappings.children.remove(getMapping(name))
    db.session.commit()


def updateMappingField(parentid, name, description="", exportformat="", mandatory=False, default="", id=0):
    mapping = q(Node).get(parentid)
    if id != "" and int(id) > 0:
        mappingfield = q(Node).get(id)
    else:
        mappingfield = MappingField(name=name)
        mapping.children.append(mappingfield)
    mappingfield.name = name
    mappingfield.setDescription(description)
    mappingfield.setExportFormat(exportformat)
    mappingfield.setMandatory(mandatory)
    mappingfield.setDefault(default)
    db.session.commit()


def deleteMappingField(name):
    node = q(Node).get(name)
    for p in node.parents:
        if p.type == "mapping":
            p.children.remove(node)
            db.session.commit()
            return


def exportMapping(name):
    if name == "all":
        return getNodeXML(q(Mappings).one())
    else:
        id = q(Node).filter_by(name=unicode(name)).one().id
        return getNodeXML(getMapping(id))


def importMapping(filename):
    n = readNodeXML(filename)
    importlist = list()
    if n.getContentType() == "mapping":
        importlist.append(n)
    elif n.getContentType() == "mappings":
        for ch in n.children:
            importlist.append(ch)

    mappings = q(Mappings).one()
    for m in importlist:
        m.name = u"import-" + m.getName()
        mappings.children.append(m)
    db.session.commit()


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
        f = list(self.children)
        f.sort(lambda x, y: cmp(x.name.lower(), y.name.lower()))
        return f

    def getMandatoryFields(self):
        ret = []
        for f in self.getFields():
            if f.getMandatory():
                ret.append(f)
        return ret

    def addField(self, field):
        self.children.append(field)

    def getFieldtype(self):
        return "mapping"

    @classmethod
    def isContainer(cls):
        return 0

    def getActive(self):
        if self.get("active") == "0":
            return 0
        return 1

    def setActive(self, value):
        if value is None:
            value = "0"
        self.set("active", ustr(value))

    def getMappingType(self):
        if self.get("mappingtype") == "":
            return "default"
        return self.get("mappingtype")

    def setMappingType(self, value):
        self.set("mappingtype", value)


@check_type_arg
class MappingField(Node):

    def getFullName(self):
        if self.getMandatory():
            return self.name + " *"
        return self.name

    def getDescription(self):
        return self.get("description")

    def setDescription(self, description):
        self.set("description", description)

    def getExportFormat(self):
        if self.get("exportformat") == "":
            m = self.getMapping()
            if m:
                return m.getStandardFormat()
            else:
                return ""
        return self.get("exportformat")

    def setExportFormat(self, exportformat):
        self.set("exportformat", exportformat)

    def getMandatory(self):
        if self.get("mandatory") == "True":
            return True
        else:
            return False

    def setMandatory(self, mandatory):
        if mandatory:
            self.set("mandatory", "True")
        else:
            self.set("mandatory", "False")

    def getMapping(self):
        return self.parents.filter_by(type=u"mapping").first()

    def getValues(self):
        return ""

    def getFieldtype(self):
        return "mappingfield"

    def getDefault(self):
        return self.get("default")

    def setDefault(self, value):
        self.set('default', value)
