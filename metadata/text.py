"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2013 Iryna Feuerstein <feuersti@in.tum.de> 

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
import core.config as config
import re
from utils.utils import esc
from utils.log import logException
from utils.pathutils import isDescendantOf
from core.metatype import Metatype,charmap
from core.translation import t
from export.exportutils import runTALSnippet



def getMaskitemForField(field, language=None, mask=None):

    mdt = [p for p in field.getParents() if p.type=='metadatatype'][0]
    
    if mask:
        masks = [mask]
    else:
        masks = [m for m in mdt.getChildren() if m.get('masktype') in ['shortview', 'fullview', 'editmask']]
        if masks and language:
            masks = [m for m in masks if m.get('language') in [language]]        
                
    maskitems = [p for p in field.getParents() if p.type=='maskitem']
    maskitems = [mi for mi in maskitems if 1 in [isDescendantOf(mi, m) for m in masks]]
       
    if maskitems:
        return maskitems[0]
    else:
        return None   

class m_text(Metatype):

    def language_snipper(self, s, language, joiner="\n"):

        if s.find(joiner) <= 0:
            return s

        valueList = s.split(joiner)

        # copied from self.getEditorHTML
        lang2value = dict()
        i = 0
        while i+1 < len(valueList):
            lang2value[valueList[i]] = valueList[i+1]
            i = i + 2

        return lang2value.get(language, '')

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None):
        lang = None
        languages = config.get("i18n.languages")
        if language==None:
            language = languages.split(",")[0].strip()
        if field.getValues() and "multilingual" in field.getValues():
            lang = [l.strip() for l in languages.split(',') if (l != language)]
        valueList = value.split("\n")
        values = dict()
        i = 0
        while i+1 < len(valueList):
            values[valueList[i]+"__"+field.getName()] = valueList[i+1]
            i = i + 2
            
        if language:
            defaultlang = language
        elif lang:
            defaultlang = lang[0]
        else:
            defaultlang = "" 
            
        context = {
            "lock": lock,
            "values": values,
            "value": value,
            "width": width,
            "name": field.getName(),
            "field": field,
            "ident": field.id if field.id else "",
            "languages": lang,
            "defaultlang": defaultlang,
            "expand_multilang": True if value.find('\n') != -1 else False
        }
        return athana.getTAL("metadata/text.html", context, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return athana.getTAL("metadata/text.html",{"context":context}, macro="searchfield", language=context.language)
    
    def getMaskEditorHTML(self, field, metadatatype=None, language=None):
        try:
            multilingual = field.getValues()
        except:
            multilingual = ""
        return athana.getTAL("metadata/text.html", {"multilingual":multilingual}, macro="maskeditor", language=language)

    def getFormatedValue(self, field, node, language=None, html=1, template_from_caller=None, mask=None):
        value = node.get(field.getName()).replace(";","; ")
        if value.find('\n') != -1:
            valuesList = value.split('\n')
            index = 0
            try:
                index = valuesList.index(language)
                value = valuesList[index+1]
            except ValueError, e:
                logException(e)
                value = ""
        unescaped_value = value

        if html:
            value = esc(value)
            
        # replace variables
        for var in re.findall( r'&lt;(.+?)&gt;', value ):
            if var=="att:id":
                value = value.replace("&lt;"+var+"&gt;", node.id)
            elif var.startswith("att:"):
                val = node.get(var[4:])
                if val=="":
                    val = "____"

                value = value.replace("&lt;"+var+"&gt;", val)
        value = value.replace("&lt;", "<").replace("&gt;",">")
        
        maskitem = getMaskitemForField(field, language=language, mask=mask)
        if not maskitem:
            return (field.getLabel(), value)        
        
        # use default value from mask if value is empty        
        if value=='':
            value = maskitem.getDefault()
    
        if template_from_caller and template_from_caller[0] and maskitem and str(maskitem.id)==template_from_caller[3]:
            value = template_from_caller[0]
        
        context = {'node':node, 'host':"http://" + config.get("host.name")}
        
        if (template_from_caller and template_from_caller[0]) and (not node.get(field.getName())):
            value = runTALSnippet(value, context)
        else: 
            try:
                value = runTALSnippet(value, context)
            except:
                value = runTALSnippet(unescaped_value, context)
                                
        return (field.getLabel(), value)

    def format_request_value_for_db(self, field, value):
        try:
            return value.replace("; ",";")
        except:
            return value

    def getName(self):
        return "fieldtype_text"
        
    def getInformation(self):
        return {"moduleversion":"1.0", "softwareversion":"1.1"}
        
    
    # method for popup methods of type text
    def getPopup(self, req):
        if "type" in req.params:
            req.writeTAL("metadata/text.html", {}, macro="javascript")
        else:
            req.writeTAL("metadata/text.html", {"charmap":charmap, "name":req.params.get("name"), "value":req.params.get("value")}, macro="popup")
        return athana.HTTP_OK
    
    # method for additional keys of type text
    def getLabels(self):
        return m_text.labels

    labels = { "de":
            [
                ("text_popup_title", "Eingabemaske f\xc3\xbcr Sonderzeichen"),
                ("fieldtype_text", "Textfeld"),
                ("fieldtype_text_desc", "Normales Texteingabefeld"),
                ("text_titlepopupbutton", "Editiermaske \xc3\xb6ffnen"),
                ("text_valuelabel", "Wert:"),
                ("text_formatedvalue", "Formatierter Wert:"),
                ("text_done", "\xC3\x9Cbernehmen"),
                ("text_cancel", "Abbrechen"),
                ("text_spcchar", "Sonderzeichen:"),
                ("text_bold_title", "Markierten Text 'Fett' setzen"),
                ("text_italic_title", "Markierten Text 'Kursiv' setzen"),
                ("text_sub_title", "Markierten Text 'tiefstellen'"),
                ("text_sup_title", "Markierten Text 'hochstellen'"),
                ("text_show_multilang", "umschalten zu mehrsprachig"),
                ("text_hide_multilang", "umschalten zu einsprachig"),                
                ("text_multilingual", "Mehrsprachigkeit aktivieren")
            ],
           "en":
            [
                ("text_popup_title", "Editor mask for specialchars"),
                ("fieldtype_text", "text field"),
                ("fieldtype_text_desc", "normal text input field"),
                ("text_titlepopupbutton", "open editor mask"),
                ("text_valuelabel", "Value:"),
                ("text_formatedvalue", "Formated Value:"),
                ("text_done", "Done"),
                ("text_cancel", "Cancel"),
                ("text_spcchar", "Special chars:"),
                ("text_bold_title", "set marked text 'bold'"),
                ("text_italic_title", "set marked text 'italic'"),
                ("text_sub_title", "set marked text 'subscript'"),
                ("text_sup_title", "set marked text 'superscript'"),
                ("text_show_multilang", "switch to multilingual"),
                ("text_hide_multilang", "switch to monolingual"),                
                ("text_multilingual", "Activate multilingual mode")
            ]
         }
