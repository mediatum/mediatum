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
import os
from utils.utils import join_paths
import logging
import core.tree
import time
import core.config

def importFile(realname,tempname):
    path,filename = os.path.split(tempname)
    uploaddir = join_paths(core.config.get("paths.datadir"),"incoming")
    try:os.mkdir(uploaddir)
    except: pass
    uploaddir = join_paths(uploaddir, time.strftime("%Y-%b"))
    try:os.mkdir(uploaddir)
    except: pass
            
    destname = join_paths(uploaddir, filename)
    if os.sep == '/':
        ret = os.system("cp "+tempname+" "+destname)
    else:
        cmd = "copy "+tempname+" "+(os.path.split(destname)[0])
        ret = os.system(cmd.replace('/','\\'))

    if ret:
        raise IOError("Couldn't copy "+tempname+" to "+destname+" (error: "+str(ret)+")")

    r = realname.lower()
    mimetype = "application/x-download"
    type = "file"
    
    mimetype, type = getMimeType(r)

    return core.tree.FileNode(name=destname,mimetype=mimetype,type=type)

