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
import codecs
import logging
import core.tree
import time

logg = logging.getLogger(__name__)


from .utils import join_paths, getMimeType, formatException


def getImportDir():
    uploaddir = join_paths(core.config.get("paths.datadir"), "incoming")
    try:
        os.mkdir(uploaddir)
    except:
        pass
    uploaddir = join_paths(uploaddir, time.strftime("%Y-%b"))
    try:
        os.mkdir(uploaddir)
    except:
        pass
    return uploaddir


def importFile(realname, tempname, prefix=""):
    try:
        path, filename = os.path.split(tempname)
        uploaddir = getImportDir()
        destname = join_paths(uploaddir, prefix + filename)

        if not os.path.exists(tempname):
            raise IOError("temporary file " + tempname + "does not exist")

        if os.path.exists(destname):  # rename if existing
            i = 0
            while os.path.exists(destname):
                i += 1
                p = prefix + ustr(i) + "_"
                destname = join_paths(uploaddir, p + filename)
                if not os.path.exists(destname):
                    prefix = p
                    break

        if os.sep == '/':
            ret = os.system('cp "%s" "%s"' % (tempname, destname))
        else:
            ret = os.system(('copy "%s" "%s"' % (tempname, destname)).replace('/', '\\'))

        if ret & 0xff00:
            raise IOError("Couldn't copy %s to %s (error: %s)" % (tempname, prefix + destname, ustr(ret)))

        r = realname.lower()
        mimetype = "application/x-download"
        type = "file"

        mimetype, type = getMimeType(r)

        return core.tree.FileNode(name=destname, mimetype=mimetype, type=type)
    except:
        logg.exception("")
    return None


def importFileFromData(filename, data, prefix=""):
    try:
        uploaddir = getImportDir()
        destname = join_paths(uploaddir, prefix + filename)

        if os.path.exists(destname):  # rename if existing
            i = 0
            while os.path.exists(destname):
                i += 1
                p = prefix + ustr(i) + "_"
                destname = join_paths(uploaddir, p + filename)
                if not os.path.exists(destname):
                    prefix = p
                    break

        with codecs.open(destname, 'wb', encoding='utf8') as file_handle:
            file_handle.write(data)

        mimetype = "application/x-download"
        type = "file"
        mimetype, type = getMimeType(filename.lower())

        return core.tree.FileNode(name=destname, mimetype=mimetype, type=type)
    except:
        logg.exception("exception in importFileFromData, ignoring")
    return None


def importFileToRealname(realname, tempname, prefix="", typeprefix=""):
    try:
        path, filename = os.path.split(realname)
        uploaddir = getImportDir()
        destname = join_paths(uploaddir, prefix + filename)

        if os.path.exists(destname):  # rename if existing
            i = 0
            while os.path.exists(destname):
                i += 1
                p = prefix + ustr(i) + "_"
                destname = join_paths(uploaddir, p + filename)
                if not os.path.exists(destname):
                    prefix = p
                    break

        if os.sep == '/':
            ret = os.system('cp "%s" "%s"' % (tempname, destname))
        else:
            ret = os.system(('copy "%s" "%s"' % (tempname, destname)).replace('/', '\\'))

        if ret & 0xff00:
            raise IOError("Couldn't copy %s to %s (error: %s)" % (tempname, prefix + destname, ustr(ret)))

        r = realname.lower()
        mimetype = "application/x-download"
        type = "file"

        mimetype, type = getMimeType(r)

        return core.tree.FileNode(name=destname, mimetype=mimetype, type=typeprefix + type)
    except:
        logg.exception("exception in importFileToRealname, ignoring")
    return None


def importFileIntoDir(destpath, tempname):
    try:
        path, filename = os.path.split(tempname)
        uploaddir = getImportDir()
        destname = destpath  # join_paths(uploaddir, filename)

        if os.sep == '/':
            ret = os.system("cp %s %s" % (tempname, destname))
        else:
            cmd = "copy %s %s" % (tempname, destname)
            ret = os.system(cmd.replace('/', '\\'))

        if ret & 0xff00:
            raise IOError("Couldn't copy %s to %s (error: %s)" % (tempname, destname, ustr(ret)))

        r = destpath.lower()
        mimetype = "application/x-download"
        type = "file"

        mimetype, type = getMimeType(r)

        return core.tree.FileNode(name=destname, mimetype=mimetype, type=type)
    except:
        logg.exception("exception in importFileIntoDir, ignoring")
    return None


def importFileRandom(tempname):
    #import core.config as config
    import random
    #import core.tree as tree
    path, filename = os.path.split(tempname)
    uploaddir = join_paths(core.config.get("paths.datadir"), "incoming")
    try:
        os.mkdir(uploaddir)
    except:
        pass
    uploaddir = join_paths(uploaddir, time.strftime("%Y-%b"))
    try:
        os.mkdir(uploaddir)
    except:
        pass

    destfile = ustr(random.random())[2:] + os.path.splitext(filename)[1]
    destname = join_paths(uploaddir, destfile)
    if os.sep == '/':
        ret = os.system("cp '%s' %s" % (tempname, destname))
    else:
        import shutil
        try:
            shutil.copyfile(tempname, destname)
            ret = None
        except Exception as e:
            logg.exception('exception when trying to importFileRandom')
            ret = e
    if ret:
        raise IOError("Couldn't copy %s to %s (error: %s)" % (tempname, destname, ret))

    r = tempname.lower()
    mimetype = "application/x-download"
    type = "file"
    mimetype, type = getMimeType(r)
    return core.tree.FileNode(name=destname, mimetype=mimetype, type=type)
    

def importFileToUploaddirWithRandomName(tempname):

    import random

    path, filename = os.path.split(tempname)
    uploaddir = getImportDir()

    destfile = ustr(random.random())[2:]+os.path.splitext(filename)[1]
    destname = join_paths(uploaddir, destfile)
    if os.sep == '/':
        ret = os.system("cp '%s' %s" %(tempname, destname))
    else:
        cmd = 'copy "%s" %s' %(tempname, destname)
        logg.debug('going to execute: ', cmd)
        ret = os.system(cmd.replace('/','\\'))

    if ret:
        raise IOError("Couldn't copy %s to %s (error: %s)" %(tempname, destname, ustr(ret)))

    r = tempname.lower()
    mimetype = "application/x-download"
    type = "file"
    mimetype, type = getMimeType(r)
    return core.tree.FileNode(name=destname, mimetype=mimetype, type=type)
