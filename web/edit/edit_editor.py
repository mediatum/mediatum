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
import os
import core.config as config
import core.users as users
from core.tree import FileNode

from lib.FCKeditor import fckeditor
from core.acl import AccessData

def edit_editor(req, node, filenode):
    user = users.getUserFromRequest(req)
    if "editor" in users.getHideMenusForUser(user):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return
        
    access = AccessData(req)

    if filenode==None:
        path = config.settings["paths.datadir"] + "html/" + req.params['id'] + ".html"
        node.addFile(FileNode(path, "content", "text/html"))
    else:
        path = filenode.retrieveFile()

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

        # delete page
        if "delete_page" in req.params:
            try:
                os.remove(req.params['file_path'])
                node.removeFile(FileNode(req.params['file_path'], "content", "text/html"))
            except:
                None

        # show editor
        try:
            os.environ['HTTP_USER_AGENT'] = req.request.request_headers['HTTP_USER_AGENT']
        except:
            os.environ['HTTP_USER_AGENT'] = req.request.request_headers['user-agent']

        oFCKeditor = fckeditor.FCKeditor('file_content_'+path)
        oFCKeditor.Width="100%"
        oFCKeditor.Height="500px"
        oFCKeditor.ToolbarSet = "mis"
        oFCKeditor.BasePath = "/module/"
        oFCKeditor.Value = getFiletemplate(req, node, path, {})

        req.writeTAL("web/edit/edit_editor.html", {"id":req.params.get('id'), "oFCKeditor":oFCKeditor, "path":path}, macro="edit_editor")
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

