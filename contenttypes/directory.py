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

from core.acl import AccessData
import re
import os
import core.athana as athana
import core.config as config
import default
from core.translation import t, lang
from utils.utils import Menu



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
        
    else:
        print "Couldn't find",file
    return ret

# taken from web/frontend/content.py 20090908 wn
def fileIsNotEmpty(file):
    f = open(file)
    s = f.read().strip()
    f.close()
    if s: return 1
    else: return 0

""" directory class """
class Directory(default.Default):
    
    def getStartpageDict(node):
        d = {}

        descriptor = node.get('startpage.selector')
        for x in descriptor.split(';'):
            if x:
                key, value = x.split(':')
                d[key]=value

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
                    if shortpath_dict == shortpath_file:
                        res = f
        if not d:
            for f in node.getFiles():
                shortpath_file = f.retrieveFile().replace(basedir, "")
                if f.getType() == 'content' and f.mimetype == 'text/html':
                    res = f

        if verbose:
            if res:
                print "getStartpageFileNode(%s, %s) is returning a FileNode: %s" % (node.id, language, str([res.retrieveFile(), res.getType(), res.mimetype]))
            else:
                print "getStartpageFileNode(%s, %s) is NOT returning a FileNode: %s" % (node.id, language, str(res))

        return res

    """ format big view with standard template """
    def show_node_big(node, req):
        content = ""
        link = "node?id="+node.id + "&amp;files=1"
        
        spn = node.getStartpageFileNode(lang(req))
        if spn:
            long_path = spn.retrieveFile()
            if os.path.isfile(long_path) and fileIsNotEmpty(long_path):
                                  content = includetemplate(node, long_path, {'${next}': link})
            if content:
                return content

        return content
    
    """ format node image with standard template """
    def show_node_image(node,language=None):
        return athana.getTAL("contenttypes/directory.html", {"node":node}, macro="thumbnail",language=language)
     
    def isContainer(node):
        return 1
    
    def getPossibleChildContainers():
        if self.type == "directory":
            return ["directory"]
        elif self.type == "collection" or self.type == "collections":
            return ["directory","collection"]
        elif self.type.startswith("directory"):
            print "special directory"
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
        menu = list()
        try:
            submenu = Menu("tab_layout", "description","#", "../") #new
            submenu.addItem("tab_content","tab_content")
            submenu.addItem("tab_startpages","tab_startpages") # new 20090906 wn
            # submenu.addItem("tab_editor","tab_editor")
            submenu.addItem("tab_view","tab_view")
            menu.append(submenu)
            submenu = None
            
            if node.getContentType().startswith("directory"):
                submenu = Menu("tab_metadata", "description","#", "../") # new
                submenu.addItem("tab_metadata_dir","tab_metadata")
            if node.getContentType() in ("collection", "collections"):
                submenu = Menu("tab_metadata", "description","#", "../") # new
                submenu.addItem("tab_metadata_col","tab_metadata")
                submenu.addItem("tab_logo","tab_logo")
            if submenu:
                submenu.addItem("tab_files","tab_files")
                submenu.addItem("tab_admin","tab_admin")
            
            if node.getContentType() in ("collection", "collections"):
                submenu.addItem("tab_searchmask","tab_searchmask")
                submenu.addItem("tab_sortfiles","tab_sortfiles")
            if submenu:
                menu.append(submenu)
            
            submenu = Menu("tab_security", "description","#", "../") # new
            submenu.addItem("tab_acls","tab_acls")
            menu.append(submenu)
            
            submenu = Menu("tab_operation", "description","#", "../") # new
            submenu.addItem("tab_search","tab_search")
            submenu.addItem("tab_subfolder","tab_subfolder")
            submenu.addItem("tab_license","tab_license")
            menu.append(submenu)

        except TypeError:
            pass
        return menu
        
    def getDefaultEditTab(node):
        return "tab_content"
    

