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
import athana
import re
from translation import *
from objtypes.metatype import Metatype

class m_url(Metatype):

    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None):
        fielddef = field.getValues().split("\r\n")
        if len(fielddef)!=3:
            fielddef = ("","","")
        val = value.split(";")
        if len(val)!=2:
            val = ("","")

        return athana.getTAL("m_url.html", {"lock":lock, "value":val, "fielddef":fielddef, "width":width, "name":name, "field":field}, macro="editorfield", language=language)


    def getSearchHTML(self, field, value="", width=174, name="", language=None):
        return athana.getTAL("m_url.html",{"field":field, "value":value, "name":name}, macro="searchfield", language=language)

    #
    # format node value depending on field definition
    #
    def getFormatedValue(self, field, node, language=None):
        try:
            value = node.get(field.getName()).split(";")
            fielddef = field.getValues().split("\r\n")

            l = ""
            for i in range(0,2):
                try:
                    if value[i]!="":
                        l += value[i] + ";"
                    else:
                        l += fielddef[i] + ";"
                except:
                    l += fielddef[i] + ";"
            fielddef = l

            # replace variables
            for var in re.findall( r'<(.+?)>', fielddef ):
                if var=="att:id":
                    fielddef = fielddef.replace("<"+var+">", node.id)
                elif var.startswith("att:"):
                    val = node.get(var[4:])
                    if val=="":
                        val = "____"

                    fielddef = fielddef.replace("<"+var+">", val)

            fielddef = fielddef.split(";")
            
            if str(fielddef[0]).find("____")>=0:
                value = str(fielddef[1])
            else:
                try:
                    value = '<a href="'+str(fielddef[0])+'" target="_blank" title="'+t(language,'show in new window')+'">'+str(fielddef[1])+'</a>' 
                except:
                    value = '<a href="'+str(fielddef[0])+'" target="_blank">'+str(fielddef[1])+'</a>'
                
            if fielddef[2]!="":
                value += ' <img src="'+str(fielddef[2])+'"/>'

            return (field.getLabel(), value)
        except:
            print "error in url-field format"
            return (field.getLabel(), "")

    def getMaskEditorHTML(self, value="", metadatatype=None, language=None):
        value = value.split("\r\n")
        while len(value)<3:
            value.append("")
        return athana.getTAL("m_url.html", {"value":value, "icons":{"externer Link":"/img/extlink.png", "Email":"/img/email.png"}}, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_url"
