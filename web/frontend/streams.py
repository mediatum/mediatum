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
import core.tree as tree
import os
import core.config as config
import core.athana as athana
from utils.utils import get_filesize, join_paths, clean_path, getMimeType, formatException
from core.translation import t
from core.styles import theme
import random
import zipfile

import glob
import utils.utils

import core.acl as acl
from core import archivemanager
from core.acl import AccessData
from core.tree import getNode
from string import atoi


IMGNAME = re.compile("/?(attachment|doc|images|thumbs|thumb2|file|download|archive)/([^/]*)(/(.*))?$")

def incUsage(node):
    nr = int(node.get("hit_statistic.file") or "0")
    nr+=1
    node.set("hit_statistic.file", str(nr))

def splitpath(path):
    m = IMGNAME.match(path)
    if m is None:
        return path
    try:
        return m.group(2), m.group(4)
    except:
        return m.group(2), None

def send_image(req):
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.getType()=="image":
            return req.sendFile(f.retrieveFile(), f.getMimeType())
    return 404
    
def send_image_watermark(req):
    try:
        result = splitpath(req.path)
        n = tree.getNode(result[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.getType()=="original_wm":
            return req.sendFile(f.retrieveFile(), getMimeType(f.retrieveFile()))
    return 404

def send_rawimage(req):
    access = AccessData(req)
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(n, "data") and n.type!="directory":
        return 403
    for f in n.getFiles():
        if f.getType()=="original":
            incUsage(n)
            return req.sendFile(f.retrieveFile(), f.getMimeType())
    return 404
    
def send_rawfile(req, n=None):
    access = AccessData(req)
    if not n:
        id, filename = splitpath(req.path)
        n = None
        try:
            n = tree.getNode(id)
        except tree.NoSuchNodeError:
            return 404

    if not access.hasAccess(n, "data") and n.getContentType() not in ["directory", "collections", "collection"]:
        return 403
    for f in n.getFiles():
        if f.getType()=="original":
            incUsage(n)
            return req.sendFile(f.retrieveFile(n), f.getMimeType(n))
    return 404

def send_thumbnail(req):
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.getType()=="thumb":
            if os.path.isfile(f.retrieveFile()):
                return req.sendFile(f.retrieveFile(), f.getMimeType())
    

    for p in athana.getFileStorePaths("/img/"):
        for test in ["default_thumb_%s_%s.*" % (n.getContentType(), n.getSchema()), "default_thumb_%s.*" % (n.getSchema()), "default_thumb_%s.*" % (n.getContentType())]:
            fps = glob.glob(os.path.join(config.basedir, p[2:], test))
            if fps:
                thumb_mimetype, thumb_type = utils.utils.getMimeType(fps[0])
                return req.sendFile(fps[0], thumb_mimetype, force=1)
    return req.sendFile(config.basedir + "/web/img/questionmark.png", "image/png", force=1)

def send_thumbnail2(req):
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.getType().startswith("presentat"):
            if os.path.isfile(f.retrieveFile()):
                return req.sendFile(f.retrieveFile(), f.getMimeType())
    #fallback
    for f in n.getFiles():
        if f.getType()=="image":
            if os.path.isfile(f.retrieveFile()):
                return req.sendFile(f.retrieveFile(), f.getMimeType())
                
    #fallback2
    for p in athana.getFileStorePaths("/img/"):
        for test in ["default_thumb_%s_%s.*" % (n.getContentType(), n.getSchema()), "default_thumb_%s.*" % (n.getSchema()), "default_thumb_%s.*" % (n.getContentType())]:
            #fps = glob.glob(os.path.join(config.basedir, theme.getImagePath(), "img", test))
            fps = glob.glob(os.path.join(config.basedir, p[2:], test))
            if fps:
                thumb_mimetype, thumb_type = utils.utils.getMimeType(fps[0])
                return req.sendFile(fps[0], thumb_mimetype, force=1)
    return 404
    

def send_doc(req):
    access = AccessData(req)
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(n, "data") and n.type!="directory":
        return 403
    for f in n.getFiles():
        if f.getType() in ["doc", "document"]:
            incUsage(n)
            if(f.getSize()>16*1048576):
                return req.sendFile(f.retrieveFile(), "application/x-download")
            else:
                return req.sendFile(f.retrieveFile(), f.getMimeType())
    return 404

def send_file(req, download=0):
    access = AccessData(req)
    id,filename = splitpath(req.path)
    if id.endswith(".zip"):
        id = id[:-4]
    
    try:
        n = tree.getNode(id)
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(n, "data") and n.type not in ["directory", "collections", "collection"]:
        return 403
    file = None
    
    if filename==None and n:
        # build zip-file and return it
        send_transferzip(req)

    # try full filename
    for f in n.getFiles():
        if f.getName()==filename:
            incUsage(n)
            file = f
            break
    # try only extension
    if not file and n.get("archive_type")=="":
        for f in n.getFiles():
            if os.path.splitext(f.getName())[1] == os.path.splitext(filename)[1]:
                incUsage(n)
                file = f
                break
    # try file from archivemanager
    if not file and n.get("archive_type")!="":
        am = archivemanager.getManager(n.get("archive_type"))
        if n.get("archive_state")=="":
            am.getArchivedFile(n.id)
        if not am:
            return
        return req.sendFile(am.getArchivedFileStream(n.get("archive_path")), "application/x-download")

    
    if not file:
        return 404

    video = file.getType()=="video"

    if((download or file.getSize()>16*1048576) and not video):
        req.reply_headers["Content-Disposition"] = "attachment; filename="+filename
        return req.sendFile(file.retrieveFile(), "application/x-download")
    else:
        return req.sendFile(file.retrieveFile(), file.getMimeType())

def send_file_as_download(req):
    return send_file(req, download=1)

def send_attachment(req):
    access = AccessData(req)
    id,filename = splitpath(req.path)
    try:
        node = tree.getNode(id)
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(node,"data") and n.type != "directory":
        return 403
    # filename is attachment.zip
    for file in node.getFiles():
        if file.getType()=="attachment":
            sendZipFile(req, file.retrieveFile())
            break

def sendZipFile(req, path):
    tempfile = join_paths(config.get("paths.tempdir"), str(random.random()))+".zip"
    zip = zipfile.ZipFile(tempfile, "w")
    zip.debug = 3
    def r(p):
        if os.path.isdir(join_paths(path, p)):
            for file in os.listdir(join_paths(path, p)):
                r(join_paths(p, file))
        else:
            while len(p)>0 and p[0]=="/":
                p = p[1:]
            try:
                zip.write(join_paths(path, p), p)
            except:
                pass
    r("/")
    zip.close()
    req.reply_headers['Content-Disposition'] = "attachment; filename=shoppingbag.zip"
    req.sendFile(tempfile, "application/x-download")
    if os.sep=='/': # Unix?
        os.unlink(tempfile) # unlinking files while still reading them only works on Unix/Linux

    
#
# send single attachment file to user
#
def send_attfile(req):
    access = AccessData(req)
    f = req.path[9:].split('/')
    try:
        node = getNode(f[0])
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(node, "data") and node.type!="directory":
        return 403
    filename = clean_path("/".join(f[1:]))
    path = join_paths(config.get("paths.datadir"), filename)
    mime, type = getMimeType(filename)
    if(get_filesize(filename) > 16*1048576):
        return req.sendFile(path, "application/x-download")
    else:
        return req.sendFile(path, mime)

        
def get_archived(req):
    id, filename = splitpath(req.path)
    n = tree.getNode(id)
    if not archivemanager:
        req.write("-no archive module loaded-")
        return
    am = archivemanager.getManager(n.get("archive_type"))
    if am:
        fname = am.getArchivedFileStream(n.get("archive_path"))
        if os.path.exists(fname):
            req.sendFile(fname, "application/x-download")
    else:
        print "no archive manager loaded"
        return 0

    
def get_root(req):
    filename = config.basedir+"/web/root"+req.path
    if os.path.isfile(filename):
        return req.sendFile(filename, "text/plain")
    else:
        return 404
        
def send_transferzip(req):
    id, filename = splitpath(req.path)
    
    # send transfer file as zip
    print "build zip", tree.getNode(id[:-4])
    return
