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
from core.xmlnode import getNodeXML, readNodeXML

def getMappings():
    try:
        mappings = tree.getRoot("mappings")
    except tree.NoSuchNodeError,e:
        root = tree.getRoot()
        root.addChild(tree.Node("mappings", "mappings"))
        mappings = tree.getRoot("mappings")
    
    try:
        return mappings.getChildren()
    except tree.NoSuchNodeError,e:
        return []


def getMapping(id):
    try:
        return tree.getNode(id)
    except tree.NoSuchNodeError,e:
        mappings = tree.getRoot("mappings")
        return mappings.getChild(id)

def getMappingTypes():
    ret = []
    try:
        mappings = tree.getRoot("mappings")
        ret = mappings.get("mappingtypes").split(";")
        if len(ret)==0 or ret[0]=="":
            mappings.set("mappingtypes", "default;bibtex;rss;marc21;z3950")
            return getMappingTypes()
        return ret
    except:
        return ret
        
def updateMapping(name, namespace="", namespaceurl="", description="", header="", footer="", separator="", standardformat="", id=0, mappingtype="", active=""):
    if id!="" and int(id)>0:
        mapping = tree.getNode(id)
    else:
        mappings = tree.getRoot("mappings")
        mapping = tree.Node(name=name, type="mapping")
        mappings.addChild(mapping)
    mapping.setName(name)
    mapping.setDescription(description)
    mapping.setNamespace(namespace)
    mapping.setNamespaceUrl(namespaceurl)
    mapping.setHeader(header)
    mapping.setFooter(footer)
    mapping.setSeparator(separator)
    mapping.setStandardFormat(standardformat)
    mapping.setMappingType(mappingtype)
    mapping.setActive(active)

def deleteMapping(name):
    mappings = tree.getRoot("mappings")
    mappings.removeChild(getMapping(name))
    
    
def updateMappingField(parentid, name, description="", exportformat="", mandatory=False, id=0):
    mapping = tree.getNode(parentid)
    if id!="" and int(id)>0:
        mappingfield = tree.getNode(id)
    else:
        mappingfield = tree.Node(name=name, type="mappingfield")
        mapping.addChild(mappingfield)
    mappingfield.setName(name)
    mappingfield.setDescription(description)
    mappingfield.setExportFormat(exportformat)
    mappingfield.setMandatory(mandatory)
    

def deleteMappingField(name):
    node = tree.getNode(name)
    for p in node.getParents():
        if p.type=="mapping":
            p.removeChild(node)
            return

            
def exportMapping(name):
    if name=="all":
        return getNodeXML(tree.getRoot("mappings"))
    else:
        return getNodeXML(getMapping(name))

        
def importMapping(filename):
    n = readNodeXML(filename)
    importlist = list()
    if n.getContentType()=="mapping":
        importlist.append(n)
    elif n.getContentType()=="mappings":
        for ch in n.getChildren():
            importlist.append(ch)

    mappings = tree.getRoot("mappings")
    for m in importlist:
        m.setName("import-"+m.getName())
        mappings.addChild(m)

        
class Mapping(tree.Node):

    def getName(self):
        return self.get("name")
    def setName(self, n):
        self.set("name", n)

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
        f = list(self.getChildren())
        f.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))
        return f
        
    def getMandatoryFields(self):
        ret = []
        for f in self.getFields():
            if f.getMandatory():
                ret.append(f)
        return ret
        
    def addField(self, field):
        self.addChild(field)
        
    def getFieldtype(self):
        return "mapping"
    
    def isContainer(node):
        return 0
        
    def getActive(self):
        if self.get("active")=="0":
            return 0
        return 1
        
    def setActive(self, value):
        if value==None:
            value = "0"
        self.set("active", str(value))
        
    def getMappingType(self):
        if self.get("mappingtype")=="":
            return "default"
        return self.get("mappingtype")
        
    def setMappingType(self, value):
        self.set("mappingtype", value)
        
        
        
class MappingField(tree.Node):
    
    def getName(self):
        return self.get("name")
    def setName(self, n):
        self.set("name", n)
        
    def getFullName(self):
        if self.getMandatory():
            return self.getName() + " *"
        return self.getName()

    def getDescription(self):
        return self.get("description")
    def setDescription(self, description):
        self.set("description", description)
        
    def getExportFormat(self):
        if self.get("exportformat")=="":
            m = self.getMapping()
            if m:
                return m.getStandardFormat()
            else:
                return ""
        return self.get("exportformat")
    def setExportFormat(self, exportformat):
        self.set("exportformat", exportformat)
        
    def getMandatory(self):
        if self.get("mandatory")=="True":
            return True
        else:
            return False
    def setMandatory(self, mandatory):
        if mandatory:
            self.set("mandatory", "True")
        else:
            self.set("mandatory", "False")
            
    def getMapping(self):
        for p in self.getParents():
            try:
                if p.getFieldtype()=="mapping":
                    return p
            except:
                pass
        return None
    def getValues(self):
        return ""
        
    def getFieldtype(self):
        return "mappingfield"
