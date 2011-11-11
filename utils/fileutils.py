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
import logging
import core.tree
import time

from utils import join_paths, getMimeType, formatException

def getImportDir():
    uploaddir = join_paths(core.config.get("paths.datadir"),"incoming")
    try: os.mkdir(uploaddir)
    except: pass
    uploaddir = join_paths(uploaddir, time.strftime("%Y-%b"))
    try: os.mkdir(uploaddir)
    except: pass
    return uploaddir


def importFile(realname,tempname, prefix=""):
    try:
        path,filename = os.path.split(tempname)
        uploaddir = getImportDir()
        destname = join_paths(uploaddir, prefix+filename)

        if os.path.exists(destname): # rename if existing
            i = 0
            while os.path.exists(destname):
                i+=1
                p = prefix + str(i)+"_"
                destname = join_paths(uploaddir, p+filename)
                if not os.path.exists(destname):
                    prefix = p
                    break

        if os.sep=='/':
            ret = os.system('cp "%s" "%s"' %(tempname, destname))
        else:
            ret = os.system(('copy "%s" "%s"' %(tempname, destname)).replace('/','\\'))

        if ret&0xff00:
            raise IOError("Couldn't copy %s to %s (error: %s)" % (tempname, prefix+destname, str(ret)))

        r = realname.lower()
        mimetype = "application/x-download"
        type = "file"
        
        mimetype, type = getMimeType(r)

        return core.tree.FileNode(name=destname,mimetype=mimetype, type=type)
    except:
        print formatException()
    return None
    
    
def importFileIntoDir(destpath, tempname):
    try:
        path,filename = os.path.split(tempname)
        uploaddir = getImportDir()
        destname = destpath# join_paths(uploaddir, filename)
        
        if os.sep=='/':
            ret = os.system("cp %s %s" %(tempname, destname))
        else:
            cmd = "copy %s %s" %(tempname, destname)
            ret = os.system(cmd.replace('/','\\'))

        if ret&0xff00:
            raise IOError("Couldn't copy %s to %s (error: %s)" % (tempname, destname, str(ret)))

        r = destpath.lower()
        mimetype = "application/x-download"
        type = "file"
        
        mimetype, type = getMimeType(r)

        return core.tree.FileNode(name=destname,mimetype=mimetype, type=type)
    except:
        print formatException()
    return None
    

def importFileRandom(tempname):
    #import core.config as config
    import random
    #import core.tree as tree
    path,filename = os.path.split(tempname)
    uploaddir = join_paths(core.config.get("paths.datadir"),"incoming")
    try:os.mkdir(uploaddir)
    except: pass
    uploaddir = join_paths(uploaddir, time.strftime("%Y-%b"))
    try:os.mkdir(uploaddir)
    except: pass

    destfile = str(random.random())[2:]+os.path.splitext(filename)[1]
    destname = join_paths(uploaddir, destfile)
    if os.sep == '/':
        ret = os.system("cp '%s' %s" %(tempname, destname))
    else:
        cmd = "copy '%s' %s" %(tempname, (os.path.split(destname)[0]))
        ret = os.system(cmd.replace('/','\\'))
 
    if ret:
        raise IOError("Couldn't copy %s to %s (error: %s)" %(tempname, destname, str(ret)))
 
    r = tempname.lower()
    mimetype = "application/x-download"
    type = "file"
    mimetype, type = getMimeType(r)
    return core.tree.FileNode(name=destname, mimetype=mimetype, type=type)
