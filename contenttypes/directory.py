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
import re
import os

import core.tree as tree
import core.athana as athana
import core.config as config
import default

from core.acl import AccessData
from core.translation import t, lang
from utils.utils import CustomItem
try:
    import web.frontend.modules.modules as frontendmods
    frontend_modules = 1
except:
    frontend_modules = 0


SRC_PATTERN = re.compile('src="([^":/]*)"')

""" these are not TAL templates, but a much more simplified version. All that
    is replaced are images and links to ${next} """
def includetemplate(node, file, substitute):
    ret = ""
    if os.path.isfile(file):
        
        fi = open(file, "rb")
        s = str(fi.read())

        for string,replacement in substitute.items():
            s = s.replace(string, replacement)
       
        lastend = 0
        scanner = SRC_PATTERN.scanner(s)
        while 1:
            match = scanner.search()
            if match is None:
                ret += s[lastend:]
                break
            else:
                ret += s[lastend:match.start()]
                imgname = match.group(1)
                ret += 'src="/file/'+node.id+'/'+imgname+'"'
                lastend = match.end()
        fi.close()
    return ret
    
    
def replaceModules(node, req, input):
    global frontend_modules
    if frontend_modules:
        frontend_mods = frontendmods.getFrontendModules()

        def getModString(m):
            for k in frontend_mods:
                if m.group(0).startswith('{frontend/'+k+'/'):
                    return m.group(0), frontend_mods[k]().getContent(req, path=m.group(0)[1:-1].replace('frontend/'+k+'/', ""))
            return "", ""
        
        while 1:
            m = re.compile('{frontend/.[^{]*}').search(input)
            if m:
                mod_str, mod_repl = getModString(m)
                input = input.replace(mod_str, mod_repl)
            else:
                break
    return input

    
def fileIsNotEmpty(file):
    f = open(file)
    s = f.read().strip()
    f.close()
    if s: return 1
    else: return 0

""" directory class """
class Directory(default.Default):
    def getTypeAlias(node):
        return "directory"
        
    def getCategoryName(node):
        return "container"

    
    def getStartpageDict(node):
        d = {}
        descriptor = node.get('startpage.selector')
        for x in descriptor.split(';'):
            if x:
                key, value = x.split(':')
                d[key] = value

        return d

    def getStartpageFileNode(node, language, verbose=False):
        res = None
        basedir = config.get("paths.datadir")
        d = node.getStartpageDict()
        
        if d and (language in d.keys()):
            shortpath_dict = d[language]
            if shortpath_dict:
                for f in node.getFiles():
                    shortpath_file = f.retrieveFile().replace(basedir, "")
                    if shortpath_dict==shortpath_file:
                        res = f
        if not d:
            for f in node.getFiles():
                shortpath_file = f.retrieveFile().replace(basedir, "")
                if f.getType()=='content' and f.mimetype=='text/html':
                    res = f
        return res

    """ format big view with standard template """
    def show_node_big(node, req, template="", macro=""):
        content = ""
        link = "node?id="+node.id + "&amp;files=1"
        sidebar = ""
        pages = node.getStartpageDict()
        if node.get("system.sidebar")!="":
            for sb in node.get("system.sidebar").split(";"):
                if sb!="":
                    l, fn = sb.split(":")
                    if l==lang(req):
                        for f in node.getFiles():
                            if fn.endswith(f.getName()):
                                sidebar = includetemplate(node,f.retrieveFile(), {})
                                sidebar = replaceModules(node, req, sidebar).strip()
        if sidebar!="":
            sidebar = req.getTAL("contenttypes/directory.html", {"content":sidebar}, macro="addcolumn")
        else:
            sidebar = ""
        
        if "item" in req.params:
            fpath = config.get("paths.datadir")+"html/"+req.params.get("item")
            if os.path.isfile(fpath):
                c = open(fpath, "r")
                content = c.read()
                c.close()
                if sidebar!="":
                    return '<div id="portal-column-one">'+content+'</div>' + sidebar 
                return content
        
        spn = node.getStartpageFileNode(lang(req))
        if spn:
            long_path = spn.retrieveFile()
            if os.path.isfile(long_path) and fileIsNotEmpty(long_path):
                content = includetemplate(node, long_path, {'${next}': link})
                content = replaceModules(node, req, content)
            if content:
                if sidebar!="":
                    return '<div id="portal-column-one">'+content+'</div>' + sidebar 
                return content

        return content + sidebar 
    
    """ format node image with standard template """
    def show_node_image(node,language=None):
        return athana.getTAL("contenttypes/directory.html", {"node":node}, macro="thumbnail",language=language)
     
    def isContainer(node):
        return 1
        
    def getSysFiles(node):
        return ["statistic", "image"]
    
    def getPossibleChildContainers():
        if self.type == "directory":
            return ["directory"]
        elif self.type == "collection" or self.type == "collections":
            return ["directory","collection"]
        elif self.type.startswith("directory"):
            return ["directory"]
        else:
            return []

    def getLabel(node):
        label = node.get("label")
        if not label:
            label = node.getName()
        return label

    """ list with technical attributes for type directory """
    def getTechnAttributes(node):
        return {}

    def getLogoPath(node):
        items = []
        for file in node.getFiles():
            if file.getType()=='image':
                items.append(file.getName())
 
        if not "system.logo" in node.attributes.keys() and len(items)==1:
            return items[0]
        else:
            logoname = node.get("system.logo")
            for item in items:
                if item==logoname:
                    return item
        return ""

    def metaFields(node, lang=None):
        ret = list()
        
        field = tree.Node("nodename", "metafield")
        field.set("label", t(lang,"node name"))
        field.set("type", "text")
        ret.append(field)
        
        if node.type.startswith("collection"):
            # special fields for collections
            field = tree.Node("style", "metafield")
            field.set("label", t(lang,"style"))
            field.set("type", "list")
            field.set("valuelist", "thumbnail;list;text")
            ret.append(field)

            #field = tree.Node("url", "metafield")
            #field.set("label", t(lang,"don't display logo"))
            #field.set("type", "text")
            #ret.append(field) no longer required
            
            field = tree.Node("style_full", "metafield")
            field.set("label", t(lang,"full view style"))
            field.set("type", "list")
            field.set("valuelist", "full_standard;full_text")
            ret.append(field)
            
            field = tree.Node("style_hide_empty", "metafield")
            field.set("label", t(lang,"hide empty directories"))
            field.set("type", "check")
            ret.append(field)
            
        elif node.type.startswith("directory"):
            # special fields for directories
            field = tree.Node("style", "metafield")
            field.set("label", t(lang,"style"))
            field.set("type", "list")
            field.set("valuelist", "thumbnail;list;text")
            ret.append(field)
            
            field = tree.Node("style_full", "metafield")
            field.set("label", t(lang,"full view style"))
            field.set("type", "list")
            field.set("valuelist", "full_standard;full_text")
            ret.append(field)
            
        return ret

        
    def getEditMenuTabs(node):
        if node.getContentType() in ["collection", "collections"]:
            return "menulayout(content;startpages;view);menumetadata(metadata;logo;files;admin;searchmask;sortfiles);menusecurity(acls);menuoperation(search;subfolder;license)"
        
        elif node.getContentType()=="directory":
            return "menulayout(content;startpages;view);menumetadata(metadata;files;admin);menusecurity(acls);menuoperation(search;subfolder;license)"

        else:
            return "menulayout(content;startpages;view);menusecurity(acls);menuoperation(search;subfolder;license)"
        
    def getDefaultEditTab(node):
        return "content"
    
    def getCustomItems(node, type=""):
        ret = []
        items = {}
        items[type] = node.get("system."+type).split(";")

        for item in items[type]:
            if item!="":
                item = item.split("|")
                if len(item)==4:
                    ci = CustomItem(item[0], item[1], item[2], item[3])
                ret.append(ci)
        return ret
        
    def setCustomItems(node, type, items):
        node.set("system."+type, ";".join(str(i) for i in items))

    def event_files_changed(node):
        print "Postprocessing node",node.id
