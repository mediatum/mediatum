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
from mediatumtal import tal
from core.transition import httpstatus
from core.metatype import Metatype

from core.translation import getDefaultLanguage

from utils.dicts import SortedDict
from contenttypes.default import languages as config_languages
import re

max_lang_length = max([len(lang) for lang in config_languages])
config_default_language = getDefaultLanguage()

class m_htmlmemo(Metatype):

    additional_attrs = ['multilang']

    CUTTER_TEMPLATE = "---%s---"
    # CUTTER_PATTERN = re.compile(r"^---(?P<lang>\w{2,5})---$")
    CUTTER_PATTERN_STRING = (r"^%s$" % CUTTER_TEMPLATE) % ("(?P<lang>\w{2,%d})" % max_lang_length)
    CUTTER_PATTERN = re.compile(CUTTER_PATTERN_STRING, re.MULTILINE)
    DEFAULT_LANGUAGE_CUTTER = CUTTER_TEMPLATE % config_default_language

    
    def has_language_cutter(self, s):
        return bool(self.CUTTER_PATTERN.search(s))


    def language_snipper(self, s, language, joiner=""):
        res = []
        append_line = True
        for line in s.splitlines(True):
            m = self.CUTTER_PATTERN.match(line.strip())
            if not m:
                if append_line:
                    res.append(line)
            else:
                if m.groupdict()["lang"]==language:
                    res = []
                    append_line = True
                else:
                    append_line = False
        return joiner.join(res)

  
    def str2dict(self, s, key_joiner="__", join_stringlists=True, only_config_langs=True):
        
        if not self.has_language_cutter(s):
            d = SortedDict()
            
            for lang in config_languages:
                if lang==config_default_language:
                   d[lang] = s
                else:
                   d[lang] = ''
            
            return d
            
        d = SortedDict()
        key = "untagged"

        value = []
        d[key] = value
        append_line = True

        for line in s.splitlines(True):
            m = self.CUTTER_PATTERN.match(line)
            if not m:
                d[key].append(line)
            else:
                if d[key] and d[key][-1] and  d[key][-1][-1] == '\n':
                    d[key][-1] = d[key][-1][0:-1]  # trailing \n belongs to found cutter
                key = m.groupdict()["lang"]
                if key in d:  # should not happen
                    print '#v' * 30
                    print __file__, "----> default language conflict for:", key
                    print "already in dict:"
                    print "d['%s'] = '%s'" % (key, str(d[key]))
                    print '#^' * 30
                value = []
                d[key] = value

        # handle unused config_languages
        for lang in config_languages:
            if not lang in d.keys():
                d[lang] = []
            
        # ignore keys not in config_languages
        if only_config_langs:
            for k in d.keys():
                if not k in config_languages:
                    del d[k]          
       
        if join_stringlists: 
            for k in d.keys():
                d[k] = ''.join(d[k])
        
        return d


    def language_update(self, old_str_all, new_str_lang, language, joiner="\n"):

        # set only_config_langs=True to delete not contigured langs when updating
        d = self.str2dict(old_str_all, join_stringlists=True, only_config_langs=True)

        d[language] = new_str_lang

        res_list = []
        for k in d.keys():
            val = d[k]
            res_list.append(self.CUTTER_TEMPLATE % k)  # how should empty values look like?
            if val:
                res_list.append(val)
        return joiner.join(res_list)


    def getEditorHTML(self, field, value="", width=400, lock=0, language=None):

        # field may not be persisted as tree.Node and therefore may not have
        # an attribute "get"
        if hasattr(field, "get"):
            enable_multilang = bool(field.get('multilang'))
        else:    
            enable_multilang = False   
        
        if not language:
            language = getDefaultLanguage()

        try:
            field_node_name = field.name
        except:
            field_node_name = None 

        context = {
                    "lock": lock, 
                    "value": value, 
                    "width": width, 
                    "name": field_node_name, 
                    "field": field, 
                    "ident": str(field.id),
                    "current_lang": language,
                    "defaultlang": language,  # not the systems default language
                    "languages": [],
                    "langdict": {language: value},
                    "language_snipper": self.language_snipper,
                    "value_is_multilang": 'single', 
                    "multilang_display": 'display: none', 
                    "enable_multilang": enable_multilang, 
                    "expand_multilang": False,                  
                  }
        
        if enable_multilang:
            lang = [l for l in config_languages if l != language]
            context.update(
                      { 
                        "languages": lang,
                        "langdict": self.str2dict(value),
                        "value_is_multilang": {True:'multi', False:'single'}[self.has_language_cutter(value)], 
                        "multilang_display": {True:'', False:'display: none'}[self.has_language_cutter(value)], 
                      } )
                      
            if enable_multilang and self.has_language_cutter(value):
                context["expand_multilang"] = True
            else:
                context["expand_multilang"] = False 
                
        s = tal.getTAL("metadata/htmlmemo.html", context, macro="editorfield", language=language)
        return s.replace("REPLACE_WITH_IDENT", str(field.id))


    def getSearchHTML(self, context):
        return tal.getTAL("metadata/htmlmemo.html",{"context":context}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1):
        value = node.get(field.getName()).replace(";","; ")
        value = self.language_snipper(value, language, joiner="\n")
        return (field.getLabel(), value)

    def getMaskEditorHTML(self, field, metadatatype=None, language=None, attr_dict={}):
    
        try:
            value = field.getValues()
        except:
            value = ""
        
        context = {
                    "value": value,
                    "additional_attrs": ",".join(self.additional_attrs), 
                  }
        
        for attr_name in self.additional_attrs:
            context[attr_name] = ''
        
        context.update(attr_dict)
        return tal.getTAL("metadata/htmlmemo.html", context, macro="maskeditor", language=language)
    
    def getPopup(self, req):
        if "type" in req.params:
            req.reply_headers['Content-Type'] = "application/javascript"
            if req.params.get('type')=="configfile":
                from core.translation import lang
                req.writeTAL("metadata/htmlmemo.html", {'lang': lang(req)}, macro="ckconfig")
            elif req.params.get('type')=="javascript":
                req.writeTAL("metadata/htmlmemo.html", {}, macro="javascript")
        return httpstatus.HTTP_OK
        
    def getName(self):
        return "fieldtype_htmlmemo"
        
    def getInformation(self):
        return {"moduleversion":"1.0", "softwareversion":"1.1"}
        
    # method for additional keys of type memo
    def getLabels(self):
        return m_htmlmemo.labels

    labels = { "de":
            [
                ("editor_memo_label","Zeichen \xc3\xbcbrig"),
                ("mask_edit_max_length","Maximall\xc3\xa4nge"),
                ("mask_edit_enable_multilang","Multilang aktivieren"),                
                ("fieldtype_htmlmemo", "HTML Memofeld"),
                ("htmlmemo_titlepopupbutton", "Editiermaske \xc3\xb6ffnen"),
                ("htmlmemo_popup_title", "Eingabemaske f\xc3\xbcr HTML formatierte Texte"),
                ("htmlmemo_valuelabel", "Wert:"),
                ("htmlmemo_show_multilang", "umschalten zu mehrsprachig"),
                ("htmlmemo_hide_multilang", "umschalten zu einsprachig"),                
            ],
           "en":
            [
                ("editor_htmlmemo_label", "characters remaining"),
                ("mask_edit_max_length","Max. length"),
                ("mask_edit_enable_multilang","activate multilang"),                  
                ("fieldtype_htmlmemo", "html memo"),
                ("htmlmemo_titlepopupbutton", "open editor mask"),
                ("htmlmemo_popup_title", "Editor mask for HTML formatted text"),
                ("htmlmemo_valuelabel", "Value:"),
                ("memo_show_multilang", "switch to multilingual"),
                ("memo_hide_multilang", "switch to monolingual"),                
            ]
         }
