"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Peter Heckl <heckl@ub.tum.de>

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

import logging
import re

from core.metatype import Metatype
from utils.utils import esc, desc, modify_tex
from utils.date import parse_date, format_date
from schema.schema import getMetadataType
import export.exportutils as exportutils
from core import Node
from core import db

logg = logging.getLogger(__name__)
q = db.query

class MappingReplacement():

    def __init__(self):
        self.description = ""

    """
        s:        input string to be replaced
        var:      variable values
        node:     node holding values
        attrnode: node with attributes to be passed
    """

    def func(self, s, var, node, attrnode):
        raise None

# define standard replacements


class MappingExtStdAttr(MappingReplacement):  # replace all 'att:X' types

    def func(self, s, var, node, attrnode):
        if var.startswith("att:"):
            if var == "att:field":
                s = s.replace("[" + var + "]", attrnode.getName())
            elif var == "att:id":
                s = s.replace("[" + var + "]", unicode(node.id))
            elif var == "att:nodename":
                s = s.replace("[" + var + "]", node.name)
            elif var == "att:filename":
                s = s.replace("[" + var + "]", node.name)
            else:
                s = s.replace("[" + var + "]", ustr(node.get(var.split(":")[-1])))
        return s


class m_mappingfield(Metatype):

    def __init__(self):
        self.extensions = [MappingExtStdAttr()]

    def addMappingExt(self, ext):
        self.extensions.append(ext)

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):

        ns = ""
        if field.get("fieldtype") == "mapping":
            field = q(Node).get(field.get("mappingfield"))
            ns = field.getMapping().getNamespace()
            if ns != "":
                ns += ":"
            format = field.getExportFormat()
            field_value = ns + field.getName()
        else:
            format = field.get("mappingfield")
            field_value = field.getName()
        format = esc(format)
        for var in re.findall(r'\[(.+?)\]', format):
            if var.startswith("att:"):
                format = format.replace("[" + var + "]", '<i>{attribute:' + var[4:] + '}</i>')
            elif var == "field":
                format = format.replace("[field]", field_value)
            elif var == "value":
                format = format.replace("[value]", '<i>{' + value + '}</i>')
            elif var == "ns":
                format = format.replace("[value]", '<i>{namspaces}</i>')
        format = format.replace("\\t", "")
        return format

    def getFormHTML(self, field, nodes, req):
        return '<b><mappingFormHTML></b><br/>'

    def getMetaHTML(self, parent, index, sub=False, language=None, fieldlist={}):
        return "<mappingfield definition>"

    def getMetaEditor(self, item, req):
        return "<editor for mappingfield>"

    def isFieldType(self):
        return False

    def subStr(self, oriString, argString):
        grp = argString.split(",")
        try:
            ret = int(grp[0])
        except ValueError:
            ret = 0
        try:
            ret2 = int(grp[1])
        except ValueError:
            ret2 = None
        return oriString[ret:ret2]

    def replaceStr(self, oriString, argString):
        m = re.match(r"[ \t]*\'([^\']*)\'[ \t]*,[ \t]*\'([^\']*)\'[ \t]*$", argString)
        if not m or len(m.groups()) != 2:
            return oriString    # syntax error; don't do anything
        return oriString.replace(m.groups()[0], m.groups()[1])

    def replaceVars(self, s, node, attrnode=None, field_value="", options=[], mask=None, raw=0, default=""):
        # if attrnode and node:
        for var in re.findall(r'\[(.+?)\]', s):
            if var.startswith("att:field|replacestring"):
                s2 = self.replaceStr(attrnode.getName(), var[24:])
                s = s.replace("[" + var + "]", s2)

            elif var.startswith("att:field|substring"):
                s2 = self.subStr(attrnode.getName(), var[20:])
                s = s.replace("[" + var + "]", s2)

            elif var == "field":
                s = s.replace("[field]", field_value)

            elif var == ("cmd:getTAL"):
                s = exportutils.handleCommand('cmd:getTAL', var, s, node, attrnode, field_value, options, mask)

            elif var.startswith("value|formatdate"):
                date_from = format_date(parse_date(node.get(attrnode.getName())), var[18:-1])
                s = s.replace("[" + var + "]", date_from)

            elif var.startswith("value|replacestring"):
                s2 = self.replaceStr(node.get(attrnode.getName()), var[20:])
                s = s.replace("[" + var + "]", s2)

            elif var.startswith("value|substring"):
                s2 = self.subStr(node.get(attrnode.getName()), var[16:])
                s = s.replace("[" + var + "]", s2)

            elif var.startswith("value|nodename"):
                try:
                    s2 = q(Node).get(node.get(attrnode.getName())).getName()
                except:
                    s2 = node.getName()
                s = s.replace("[" + var + "]", s2)

            elif var == "value":
                v = getMetadataType(attrnode.getFieldtype()).getFormattedValue(attrnode, None, None, node, "")[1]
                if v == "":
                    v = node.get(attrnode.getName())
                if v == "" and default != "":
                    v = default
                if "t" in options and not v.isdigit():
                    v = '"' + v + '"'
                s = s.replace("[value]", v)

            elif var == "ns":
                ns = ""
                for mapping in attrnode.get("exportmapping").split(";"):
                    n = q(Node).get(mapping)
                    if n.getNamespace() != "" and n.getNamespaceUrl() != "":
                        ns += 'xmlns:' + n.getNamespace() + '="' + n.getNamespaceUrl() + '" '
                s = s.replace("[" + var + "]", ns)

            for ext in self.extensions:
                s = ext.func(s, var, node, attrnode)
        if raw == 1:
            return s

        ret = ""
        for i in range(0, len(s)):
            if s[i - 1] == '\\':
                if s[i] == 'r':
                    ret += "\r"
                elif s[i] == 'n':
                    ret += "\n"
                elif s[i] == 't':
                    ret += "\t"
            elif s[i] == '\\':
                pass
            else:
                ret += s[i]
        return desc(ret)

    def getViewHTML(self, fields, nodes, flags, language="", template_from_caller=None, mask=None):
        ret = ""
        node = nodes[0]

        mask = fields[0].parents.first()
        separator = ""

        if mask.getMappingHeader() != "":
            ret += mask.getMappingHeader() + "\r\n"

        field_vals = []

        for field in fields:
            attribute_nid = field.get("attribute", None)
            if attribute_nid is None:
                continue

            try:
                attribute_nid = int(attribute_nid)
            except ValueError:
                logg.warn("ignoring field # %s with invalid attribute id: '%r'", field.id, attribute_nid)
                continue

            attrnode = q(Node).get(attribute_nid)
            if attrnode is None:
                continue

            if field.get("fieldtype") == "mapping":  # mapping to mapping definition
                exportmapping_id = mask.get("exportmapping").split(";")[0]
                mapping = q(Node).get(exportmapping_id)
                if mapping is None:
                    logg.warn("exportmapping %s for mask %s not found", exportmapping_id, mask.id)
                    return u""
                separator = mapping.get("separator")

                ns = mapping.getNamespace()
                if ns != "":
                    ns += ":"
                fld = q(Node).get(field.get("mappingfield"))
                format = fld.getExportFormat()
                field_value = ns + fld.getName()
                default = fld.getDefault().strip()
            else:  # attributes of node
                format = field.get("mappingfield")
                field_value = ""
                default = ""

            field_vals.append(self.replaceVars(format, node, attrnode, field_value, options=mask.getExportOptions(), mask=mask, default=default))

        if not mask.hasExportOption("l"):
            ret += separator.join(field_vals)
        else:
            ret += u"".join(field_vals)

        if mask.getMappingFooter() != "":
            ret += "\r\n" + mask.getMappingFooter()

        ret = modify_tex(ret, 'strip')

        return self.replaceVars(ret, node, mask)
