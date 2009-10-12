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
import cgi
import re
import os, sys
import string
import logging
import core.athana as athana
import core.config as config
import core.users as users
from core.tree import FileNode

from lib.FCKeditor import fckeditor
from core.acl import AccessData
from core.translation import t, lang

from web.edit import edit_startpages

def edit_editor(req, node, filenode):
    
    user = users.getUserFromRequest(req)
    access = AccessData(req)
    
    basedir = config.get("paths.datadir")
    
    file_to_edit = req.params.setdefault('file_to_edit', '')
    
    descriptiveName = node.get("startpagedescr."+file_to_edit)
    
    if descriptiveName:
        descriptiveLabel = "%s" % descriptiveName
    elif file_to_edit:
        descriptiveLabel = "%s - %s" % (t(lang(req), "edit_startpages_technical_name"), file_to_edit)
    elif filenode:
        descriptiveLabel = "Name of the file node: %s" % filenode.getName()
    else:
        descriptiveLabel = ""

    if not access.hasWriteAccess(node) or "editor" in users.getHideMenusForUser(user):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return "error"
    
    # add page
    if "add_page" in req.params:

        filelist = []
        for f in node.getFiles():
            if f.mimetype=='text/html':
                filelist.append(f)
                
        shortpaths = [f.retrieveFile().replace(basedir, "") for f in filelist]
                
        i=1
        shortpath_to_check = "html/%s_%d.html" % (node.id, i)
        while (shortpath_to_check in shortpaths) or (os.path.exists(os.path.join(basedir, shortpath_to_check))):
            i = i+1
            shortpath_to_check = "html/%s_%d.html" % (node.id, i)

        shortpath = "html/" + (node.id+"_%d" % i) + ".html"
        path = basedir + shortpath
        filenode = FileNode(path, "content", "text/html")
        descriptiveLabel = "%s - %s" % (t(lang(req), "edit_editor_new_file"), shortpath)
        node.addFile(filenode)
        logging.getLogger('usertracing').info(user.name + " - startpages - added FileNode for node %s (%s): %s, %s " % (node.id, node.name, filenode.getName(), filenode.mimetype))
    
    if filenode == None:
        filenode = node.getStartpageFileNode(lang(req))
        
    if filenode == None:
        path = os.path.join(config.settings["paths.datadir"], "html/"+req.params['id']+".html")
        for f in node.getFiles():
            if f.retrieveFile() == path:
                filenode = f

    if access.hasWriteAccess(node):
        # save page
        if "save_page" in req.params:
            content=""
            for key in req.params.keys():
                if key.startswith("file_content"):
                    content= req.params.get(key,"")
                    break
            
            fi = open(req.params['file_path'],"w")
            fi.writelines(content)
            fi.close()
            
            del req.params['save_page']
            req.params['tab'] = 'tab_startpages'
            
            path = req.params['file_path']
            
            edit_startpages.edit_startpages(req, node)
            return
                
        # delete page
        if "delete_page" in req.params:
            try:
                file_path = req.params['file_path']
                file_shortpath = file_path.replace(basedir, "")
                if os.path.exists(file_path):
                    os.remove(file_path)
                filenode = FileNode(file_path, "", "text/html")
                
                node.removeAttribute("startpagedescr."+file_shortpath)
                startpage_selector = node.get("startpage.selector").replace(file_shortpath, "")
                node.set("startpage.selector", startpage_selector)
                node.removeFile(filenode)
                
                logging.getLogger('usertracing').info(user.name + " - startpages - deleted FileNode and file for node %s (%s): %s, %s, %s" % (node.id, node.name, req.params['file_path'], filenode.getName(), filenode.mimetype))
                
            except:
                logging.getLogger('usertracing').error(user.name + " - startpages - error while delete FileNode and file for " + req.params['file_path'])
                logging.getLogger('usertracing').error("%s - %s" % ( sys.exc_info()[0], sys.exc_info()[1]))
                
            del req.params['delete_page']
            req.params['tab'] = 'tab_startpages'

            edit_startpages.edit_startpages(req, node)
            return

        path = filenode.retrieveFile()
        
        # show editor
        try:
            os.environ['HTTP_USER_AGENT'] = req.request.request_headers['HTTP_USER_AGENT']
        except:
            os.environ['HTTP_USER_AGENT'] = req.request.request_headers['user-agent']

        # these configurations override those in the custom configuration file
        # the configurations in the custom configuration file overide those in fckconfig.js
        oFCKeditor = fckeditor.FCKeditor('file_content_'+path)
        oFCKeditor.BasePath = "/module/"
        oFCKeditor.Config['CustomConfigurationsPath']='/js/custom_config.js'
        oFCKeditor.Width="100%"
        oFCKeditor.Height="500px"
        oFCKeditor.ToolbarSet = 'mediatum'
        oFCKeditor.Value = getFiletemplate(req, node, path, {})
        oFCKeditor.Config['AutoDetectLanguage'] = 'false'  # boolean javascript
        oFCKeditor.Config['DefaultLanguage'] = lang(req)
        oFCKeditor.Config['ImageBrowserURL'] = ('/edit/nodefile_browser/%s/' % node.id)
        oFCKeditor.Config['LinkBrowserURL'] = ('/edit/nodefile_browser/%s/' % node.id)
        oFCKeditor.Config['ImageUploadURL'] = ('/edit/upload_for_html/%s/' % node.id)

        v = {
             "id":req.params.get('id'),
             "oFCKeditor":oFCKeditor,
             "path":path,
             "node":node,
             "filenode":filenode,
             "files":node.getFiles(),
             "logoname":node.get("system.logo"),
             "delbutton":False,
             "descriptiveLabel":descriptiveLabel,
            }
             
        req.writeTAL("web/edit/edit_editor.html", v, macro="edit_editor")
    else:
        req.writeTAL("web/edit/edit_editor.html", {}, macro="header")
        req.write(getFiletemplate(req, node, path, {}))



SRC_PATTERN = re.compile('src="([^":/]*)"')

def getFiletemplate(req, node, file, substitute):
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
    else:
        return ""

