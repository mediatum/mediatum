"""
 mediatum - a multimedia content repository

 Copyright (C) 2008 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2008 Matthias Kramm <kramm@in.tum.de>

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
import os
import sys
import re
import string
import logging
import core.acl as acl
import core.users as users
import core.config as config

from utils.utils import getMimeType, splitpath, format_filesize
from utils.fileutils import importFile
from core.translation import translate, lang, t
from core.acl import AccessData
from lib.FCKeditor import fckeditor
from core.tree import FileNode
from web.edit.edit_common import send_nodefile_tal, upload_for_html


def edit_editor(req, node, filenode):
    user = users.getUserFromRequest(req)
    access = AccessData(req)
    
    if not access.hasWriteAccess(node) or "editor" in users.getHideMenusForUser(user):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")
    
    basedir = config.get("paths.datadir")
    file_to_edit = req.params.setdefault('file_to_edit', '')
    descriptiveName = node.get("startpagedescr."+file_to_edit)
    descriptiveLabel = ""
    
    if descriptiveName:
        descriptiveLabel = "%s" % descriptiveName
    elif file_to_edit:
        descriptiveLabel = "%s - %s" % (t(lang(req), "edit_startpages_technical_name"), file_to_edit)
    elif filenode:
        descriptiveLabel = "Name of the file node: %s" % filenode.getName()

    # add page
    if "add_page" in req.params:

        filelist = []
        for f in node.getFiles():
            if f.mimetype=='text/html':
                filelist.append(f)
                
        shortpaths = [f.retrieveFile().replace(basedir, "") for f in filelist]
                
        def getStartpageID(f):
            path = f.retrieveFile()
            id = None
            if path:
                id = os.path.split(path)[-1]
            return id

        def id2name(id):
            return dnames.setdefault(id, "")

        id_filelist = [getStartpageID(f).split('.')[0] for f in filelist]

        i = 1
        shortpath_to_check = "html/%s_%d.html" % (node.id, i)
        while (shortpath_to_check in shortpaths) or (os.path.exists(os.path.join(basedir, shortpath_to_check))):
            i += 1
            shortpath_to_check = "html/%s_%d.html" % (node.id, i)

        shortpath = "html/" + (node.id+"_%d" % i) + ".html"
        path = basedir + shortpath
        filenode = FileNode(path, "content", "text/html")
        descriptiveLabel = "%s - %s" % (t(lang(req), "edit_editor_new_file"), shortpath)
        node.addFile(filenode)
        logging.getLogger('usertracing').info(user.name + " - startpages - added FileNode for node %s (%s): %s, %s, %s " % (node.id, node.name, filenode.getName(), filenode.type, filenode.mimetype))
    
    if not filenode:
        filenode = node.getStartpageFileNode(lang(req))
        
    if not filenode:
        path = os.path.join(config.settings["paths.datadir"], "html/"+req.params['id']+".html")
        for f in node.getFiles():
            if f.retrieveFile()==path:
                filenode = f

    if access.hasWriteAccess(node):
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
        oFCKeditor.Value = getFileTemplate(req, node, path, {})
        oFCKeditor.Config['AutoDetectLanguage'] = 'false'  # boolean javascript
        oFCKeditor.Config['DefaultLanguage'] = lang(req)       
        oFCKeditor.Config['ImageBrowserURL'] = ('/edit/edit_content/%s/startpages/filebrowser' % node.id)
        oFCKeditor.Config['LinkBrowserURL'] = ('/edit/edit_content/%s/startpages/filebrowser' % node.id)
        oFCKeditor.Config['ImageUploadURL'] = ('/edit/edit_content/%s/startpages/htmlupload' % node.id)
        
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
             
        return req.getTAL("web/edit/modules/startpages.html", v, macro="edit_editor")
    else:
        return req.getTAL("web/edit/modules/startpages.html", {}, macro="header") + getFileTemplate(req, node, path, {})

        
def getFileTemplate(req, node, file, substitute):
    ret = ""
    SRC_PATTERN = re.compile('src="([^":/]*)"')
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
        
def send_fckfile(req, download=0):
    id = req.params.get("id")
    filename = req.params.get("option")

    try:
        n = tree.getNode(id)
    except tree.NoSuchNodeError:
        return 404
    access = AccessData(req)
    if not (access.hasAccess(n,'read') and access.hasAccess(n,'data')):
        return 403
    if not access.hasAccess(n,"write") and n.type not in ["directory","collections","collection"]:
        return 403
    file = None
    # try full filename
    for f in n.getFiles():
        if f.getName() == filename:
            file = f
            break

    if file and not os.path.isfile(file.retrieveFile()) and n.get("archive_type")!="":
        archivemanager.getManager(n.get("archive_type")).getArchivedFile(id)

    if not file:
        return 404

    if req.params.get("delete", "")=="True":
        user = users.getUserFromRequest(req)
        logging.getLogger('editor').info(user.name + " going to remove "+file.retrieveFile()+" via startpage editor on node " + id)
        n.removeFile(file)
        try:
            os.remove(file.retrieveFile())
        except:
            logException("could not remove file: %s" % file.retrieveFile())
        return

    return req.sendFile(file.retrieveFile(), file.getMimeType())


def getContent(req, ids):
    if "option" in req.params:
        if req.params.get("option")=="filebrowser":
            # open filebrowser
            req.write(send_nodefile_tal(req))
            return ""
            
        if req.params.get("option")=="htmlupload":
            # use fileupload
            req.write(upload_for_html(req))
            return ""

        if "delete" in req.params:
             # delete file via fck
            send_fckfile(req)
            return ""

            
    user = users.getUserFromRequest(req)
    access = AccessData(req)
    node = tree.getNode(ids[0])

    for key in req.params:
        if key.startswith("add_page"):
            del req.params[key]
            req.params["add_page"] = ""
            return  edit_editor(req, node, None)

    if "file_to_edit" in req.params and not "save_page" in req.params:
        # edit page
        file_to_edit = req.params.get("file_to_edit", None)
        if not file_to_edit:
            d = node.getStartpageDict()
            if d and lang(req) in d:
                file_to_edit = d[lang(req)]

        for f in [file for file in node.getFiles() if file.mimetype=="text/html"]:
            filepath = f.retrieveFile().replace(config.get("paths.datadir"), '')
            if file_to_edit==filepath:
                return edit_editor(req, node, f)
        return edit_editor(req, node, None)

    if access.hasWriteAccess(node):
    
        for key in req.params.keys():
            if key.startswith("delete_"): # delete page
                page = key[7:-2]
                try:
                    file_shortpath = page.replace(config.get("paths.datadir"), "")
                    if os.path.exists(page):
                        os.remove(page)
                    filenode = FileNode(page, "", "text/html")
                    
                    node.removeAttribute("startpagedescr."+file_shortpath)
                    node.set("startpage.selector", node.get("startpage.selector").replace(file_shortpath, ""))
                    node.removeFile(filenode)
                    logging.getLogger('usertracing').info(user.name + " - startpages - deleted FileNode and file for node %s (%s): %s, %s, %s, %s" % (node.id, node.name, page, filenode.getName(), filenode.type, filenode.mimetype))
                except:
                    logging.getLogger('usertracing').error(user.name + " - startpages - error while delete FileNode and file for " + page)
                    logging.getLogger('usertracing').error("%s - %s" % ( sys.exc_info()[0], sys.exc_info()[1]))
                break

        # save page
        if "save_page" in req.params:
            content = ""
            for key in req.params.keys():
                if key.startswith("file_content_"):
                    content = req.params.get(key, "")
                    break
                    
            fi = open(req.params.get('file_path'), "w")
            fi.writelines(content)
            fi.close()
            
            del req.params['save_page']
            del req.params['file_to_edit']
            req.params['tab'] = 'startpages'
            return getContent(req, [node.id])
        
        if "cancel_page" in req.params:
            del req.params['cancel_page']
            return getContent(req, [node.id])

    if not access.hasWriteAccess(node) or "editor" in users.getHideMenusForUser(user):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")
    
    filelist = []
    for f in node.getFiles():
        if f.mimetype=='text/html' and f.getType() in ['content']:
            filelist.append(f)
            
    languages = [language.strip() for language in config.get("i18n.languages").split(",")]
    
    if "startpages_save" in req.params.keys():
        descriptors  = [k for k in req.params if k.startswith('descr.') ]
        for k in descriptors:
            node.set('startpage'+k, req.params[k])
            
        # build startpage_selector
        startpage_selector = ""
        for language in languages:
            startpage_selector += "%s:%s;" % (language, req.params.get('radio_'+language))
        node.set('startpage.selector', startpage_selector[0:-1])
        
    named_filelist = []
    for f in filelist:
        long_path = f.retrieveFile()
        short_path = long_path.replace(config.get("paths.datadir"), '')
        
        file_exists = os.path.isfile(long_path)
        file_size = "-"
        if file_exists:
            file_size = os.path.getsize(long_path)
            
        langlist = []
        for language in languages:
            spn = node.getStartpageFileNode(language)
            if spn and spn.retrieveFile()==long_path:
                langlist.append(language)

        named_filelist.append( (short_path,
                                node.get('startpagedescr.'+short_path),
                                f.type,
                                f,
                                file_exists,
                                format_filesize(file_size),
                                long_path,
                                langlist,
                                "/file/%s/%s" % (req.params.get("id","0"), short_path.split('/')[-1])
                              ) )
                              
    lang2file = node.getStartpageDict()
    
    # compatibility: there may be old startpages in the database that
    # are not described by node attributes
    #initial = False
    #if filelist and not lang2file:
    #    initial = True
    initial = filelist and not lang2file
       
    # node may not have startpage set for some language
    # compatibilty: node may not have attribute startpage.selector
    # build startpage_selector and wriote back to node
    startpage_selector = ""
    for language in languages: 
        if initial:
            lang2file[language] = named_filelist[0][0]
        else:
            lang2file[language] = lang2file.setdefault(language, '')
        startpage_selector += "%s:%s;" % (language, lang2file[language])
    
    node.set('startpage.selector', startpage_selector[0:-1])

    v = {}
    v["id"] =  req.params.get("id","0")
    v["tab"] = req.params.get("tab", "")
    v["node"] = node
    v["named_filelist"] = named_filelist
    v["languages"] = languages
    v["lang2file"] = lang2file
    v["types"] = ['content']
    v["d"] =  lang2file and True
   
    return req.getTAL("web/edit/modules/startpages.html", v, macro="edit_startpages")

