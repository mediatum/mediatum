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
import string
import logging
import core.acl as acl
import core.users as users
import core.config as config

from utils.utils import getMimeType, splitpath
from utils.fileutils import importFile
from core.translation import translate, lang, t

def edit_startpages(req, node):
    user = users.getUserFromRequest(req)
    access = acl.AccessData(req)

    if not access.hasWriteAccess(node) or "editor" in users.getHideMenusForUser(user):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return "error"
    
    filelist = []
    for f in node.getFiles():
        if f.mimetype=='text/html' and f.getType() in ['content']:
            filelist.append(f)
            
    languages = [language.strip() for language in config.get("i18n.languages").split(",")]
    current_language = lang(req)
    
    if "startpages_save" in req.params.keys():
        d = req.params
        
        descriptors  = [k for k in d if k.startswith('descr.') ]
        
        for k in descriptors:
            node.set('startpage'+k, d[k])
            
        # build startpage_selector
        startpage_selector = ""
        for language in languages:
            startpage_selector += "%s:%s;" % (language, req.params.get('radio_'+language))
        startpage_selector = startpage_selector[0:-1] # remove trailing ';'
        node.set('startpage.selector', startpage_selector)
        
    basedir = config.get("paths.datadir")
    
    named_filelist = []
    for f in filelist:
        long_path = f.retrieveFile()
        short_path = long_path.replace(basedir, '')
        
        file_exists = os.path.isfile(long_path)
        file_size = "-"
        if file_exists:
            file_size = os.path.getsize(long_path)
            
        langlist = []
        for language in languages:
            spn = node.getStartpageFileNode(language)
            if spn:
                if spn.retrieveFile() == long_path:
                    langlist.append(language)
                
        link = "/file/%s/%s" % (req.params.get("id","0"), short_path.split('/')[-1])
        
        named_filelist.append( (short_path,
                                node.get('startpagedescr.'+short_path),
                                f.type,
                                f,
                                file_exists,
                                file_size,
                                long_path,
                                langlist,
                                link
                              ) )
                              
    lang2file = node.getStartpageDict()
    
    # compatibility: there may be old startpages in the database that
    # are not described by node attributes
    initial = False
    if filelist and not lang2file:
        initial = True
    
    d = False
    if  lang2file:
        d = True
        
    # node may not have startpage set for some language
    for x in languages: 
        if initial:
            lang2file[x] = named_filelist[0][0]
        else:
            lang2file[x] = lang2file.setdefault(x, '')
        
    # compatibilty: node may not have attribute startpage.selector
    # build startpage_selector and wriote back to node
    startpage_selector = ""
    for x in languages:
        startpage_selector += "%s:%s;" % (x, lang2file[x])
    startpage_selector = startpage_selector[0:-1] # remove trailing ';'
    node.set('startpage.selector', startpage_selector)
        
    types = ['content']
    
    return req.writeTAL("web/edit/edit_startpages.html",
                        {"id":req.params.get("id","0"),
                         "tab":req.params.get("tab", ""),
                         "node":node,
                         "named_filelist":named_filelist,
                         "languages":languages,
                         "lang2file":lang2file,
                         "types":types,
                         "d": d,
                        },
                        macro="edit_startpages")


