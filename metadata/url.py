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
import core.athana as athana
import re
from core.metatype import Metatype
from core.translation import t

class m_url(Metatype):

    icons = {"externer Link":"/img/extlink.png", "Email":"/img/email.png"}
    targets = {"selbes Fenster":"same", "neues Fenster":"_blank"}

    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None):
        fielddef = field.getValues().split("\r\n")
        if len(fielddef)!=3:
            fielddef = ("","","")
        val = value.split(";")
        if len(val)!=2:
            val = ("","")

        return athana.getTAL("metadata/url.html", {"lock":lock, "value":val, "fielddef":fielddef, "width":width, "name":name, "field":field}, macro="editorfield", language=language)

    def getAdminFieldsHTML(self, values={}):
        print "addfields attribute html for field-editor"
        return athana.getTAL("metadata/url.html",{"valuelist":values["valuelist"], "icons":m_url.icons,"url_targets":m_url.targets}, macro="fieldeditor", language=values["language"])
        
        
    def getSearchHTML(self, context):
        return athana.getTAL("metadata/url.html",{"context":context}, macro="searchfield", language=context.language)

    #
    # format node value depending on field definition
    #
    def getFormatedValue(self, field, node, language=None, html=1):
        try:
            value = node.get(field.getName()).split(";")
            fielddef = field.getValues().split("\r\n")

            l = ""
            for i in range(0,4):
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
                fielddef[0] = ''               
            if str(fielddef[1]).find("____")>=0:
                fielddef[1] = ''

            if len(fielddef)<4:
                fielddef[3]==""
            
            if fielddef[0]=='' and fielddef[1]=='': # link + text empty
                value = ''
            elif fielddef[0]=='' and fielddef[1]!='': # link empty, text not empty
                value = fielddef[1]
            elif fielddef[0]!='' and fielddef[1]=='':
                value = ''
            else:
                if fielddef[3] in ["","_blank"]:
                    value = '<a href="'+str(fielddef[0])+'" target="_blank" title="'+t(language,'show in new window')+'">'+str(fielddef[1])+'</a>' 
                else:
                    value = '<a href="'+str(fielddef[0])+'">'+str(fielddef[1])+'</a>' 
            if fielddef[2]!="":
                value += ' <img src="'+str(fielddef[2])+'"/>'

            return (field.getLabel(), value)
        except:
            print "error in url-field format"
            return (field.getLabel(), "")

    def getMaskEditorHTML(self, value="", metadatatype=None, language=None):
        value = value.split("\r\n")
        while len(value)<4:
            value.append("")
        return athana.getTAL("metadata/url.html", {"value":value, "icons":m_url.icons, "url_targets":m_url.targets}, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_url"
        
    def getInformation(self):
        return {"moduleversion":"1.1", "softwareversion":"1.1"}

    # method for additional keys of type url
    def getLabels(self):
        return m_url.labels
        
    labels = { "de":
            [
                ("url_edit_link", "Link:"),
                ("url_edit_linktext", "Angezeigter Text:"),
                ("url_edit_icon", "Icon:"),
                ("url_edit_noicon", "-kein Icon-"),
                ("url_edit_preview", "Vorschau:"),
                ("url_urltarget", "Linkziel:"),
                ("fieldtype_url", "URL"),
                ("fieldtype_url_desc", "externer Link (neues Fenster)")

            ],
           "en":
            [
                ("url_edit_link", "Link:"),
                ("url_edit_linktext", "Link Text:"),
                ("url_edit_icon", "Icon:"),
                ("url_edit_noicon", "-kein Icon-"),
                ("url_edit_preview", "Preview:"),
                ("url_urltarget", "Link target:"),
                ("fieldtype_url", "url"),
                ("fieldtype_url_desc", "external link (new window)")

            ]
         }
  