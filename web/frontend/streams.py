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
from utils import get_filesize,join_paths
import random
import zipfile
import core.acl as acl
from core.acl import AccessData
from core.tree import getNode


IMGNAME = re.compile("/?(attachment|doc|images|thumbs|thumb2|file)/([^/]*)(/(.*))?$")

def splitpath(path):
    m = IMGNAME.match(path)
    if m is None:
        return path
    try:
        return m.group(2),m.group(4)
    except:
        return m.group(2),None

def send_image(req):
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.type == "image":
            return req.sendFile(f.getPath(), f.getMimeType())
    return 404

def send_rawimage(req):
    access = AccessData(req)
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(n,"data") and n.type != "directory":
        return 403
    for f in n.getFiles():
        if f.type == "original":
            return req.sendFile(f.getPath(), f.getMimeType())
    return 404

def send_thumbnail(req):
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.type == "thumb":
            if os.path.isfile(f.getPath()):
                return req.sendFile(f.getPath(), f.getMimeType())
            else:
                return req.sendFile(config.basedir + "/img/questionmark.png", "image/png", force=1)
    return req.sendFile(config.basedir + "/img/questionmark.png", "image/png", force=1)

def send_thumbnail2(req):
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    for f in n.getFiles():
        if f.type.startswith("presentat"):
            return req.sendFile(f.getPath(), f.getMimeType())
    #fallback
    for f in n.getFiles():
        if f.type == "image":
            return req.sendFile(f.getPath(), f.getMimeType())
    print "No thumb2 for id",req.path
    return 404


def send_doc(req):
    access = AccessData(req)
    try:
        n = tree.getNode(splitpath(req.path)[0])
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(n,"data") and n.type != "directory":
        return 403
    for f in n.getFiles():
        if f.type == "doc":
            if(get_filesize(f.getPath()) > 16*1048576):
                return req.sendFile(f.getPath(), "application/x-download")
            else:
                return req.sendFile(f.getPath(), f.getMimeType())
    print "Document",req.path,"not found"
    return 404

def send_file(req):
    access = AccessData(req)
    id,filename = splitpath(req.path)
    try:
        n = tree.getNode(id)
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(n,"data") and n.type not in ["directory","collections"]:
        return 403
    for f in n.getFiles():
        if os.path.basename(f.path) == filename:
            if(get_filesize(f.getPath()) > 16*1048576):
                return req.sendFile(f.getPath(), "application/x-download")
            else:
                return req.sendFile(f.getPath(), f.getMimeType())
    print "Document",req.path,"not found"
    return 404

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
        if file.type == "attachment":
            sendZipFile(req,file.getPath())
            break

def sendZipFile(req, path):
    tempfile = join_paths(config.get("paths.tempdir"), str(random.random()))
    zip = zipfile.ZipFile(tempfile,"w")
    def r(p):
        if os.path.isdir(join_paths(path,p)):
            for file in os.listdir(join_paths(path,p)):
                    r(join_paths(p,file))
        else:
            zip.write(join_paths(path,p),p)
    r("")
    zip.close()
    req.sendFile(tempfile, "application/zip")
    if os.sep == '/': # Unix?
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
    if not access.hasAccess(node,"data") and node.type != "directory":
        return 403
    filename = clean_path("/".join(f[1:]))
    path = join_paths(config.get("paths.datadir"), filename)
    mime, type= getMimeType(filename)

    if(get_filesize(filename) > 16*1048576):
        return req.sendFile(path, "application/x-download")
    else:
        return req.sendFile(path, mime)
