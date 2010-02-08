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
import re
import core.tree as tree
import os
import Image
import sys
import zipfile
import core.config as config
from utils.dicts import MaxSizeDict
from utils.fileutils import importFile, getImportDir
IMGNAME = re.compile("/?tile/([^/]*)(/(.*))?$")

store = 1 # keep tiles?

cache = MaxSizeDict(16) # keep at max 16 images in memory at once

def splitpath(path):
    m = IMGNAME.match(path)
    if m is None:
        return path
    try:
        return m.group(1),m.group(3)
    except:
        return m.group(1),None

TILESIZE = 256

def getImage(nid, preprocess=0):
    global cache
    if nid in cache:
        return cache[nid]

    node = tree.getNode(nid)
    img = ZoomImage(node, preprocess)
    cache[nid] = img
    return img

class ZoomImage:
    def __init__(self, node, preprocess=0):
        self.node = node
        self.width = int(self.node.get("width"))
        self.height = int(self.node.get("height"))
        self.levels = int(self.node.get("levels") or "0")
        self.img = None
        self.z_file = None
        self.filepath = None
        self.load()
        
        if not self.levels:
            self.load()
        if store and preprocess:
            self.preprocess()

    def load(self):
        if self.img:
            return

        for f in self.node.getFiles():
            if f.type == "image":
                filename = f.retrieveFile()
                self.filepath = os.path.dirname(filename)
                break
        else:
            raise AttributeError("Not an image")

        self.img = Image.open(filename)
        self.img.load()
        l = max(self.img.size)
        self.levels = 0
        while l > TILESIZE:
            l = l/2
            self.levels = self.levels + 1
        self.width,self.height = self.img.size
        self.node.set("levels", str(self.levels))

    def preprocess(self):
        names = []
        for level in range(self.levels+1):
            t = (TILESIZE<<(self.levels-level))
            for x in range((self.width + (t-1)) / t):
                for y in range((self.height + (t-1)) / t):
                    names.append(self.getTile(level, x, y, 1))

        # open the zip file for writing, and write stuff to it
        file = zipfile.ZipFile(self.filepath+"/zoom"+str(self.node.id)+".zip", "w")
        for name in names:
            file.write(name, os.path.basename(name), zipfile.ZIP_DEFLATED)
            os.unlink(name)
        file.close()
        
        self.node.addFile(tree.FileNode(name=getImportDir()+"/zoom"+str(self.node.id)+".zip",mimetype="application/zip",type="zoom"))


    def getTile(self, level, x, y, generate=0):
        if level > self.levels:
            return None

        tileid = "tile-%d-%d-%d" % (level,x,y)

        if not self.z_file:
            for f in self.node.getFiles():  
                if f.type=="zoom":
                    self.z_file = zipfile.ZipFile(self.filepath+"/"+f.getName(), "r")
                    break
        if self.z_file:
            return self.z_file.read(tileid+".jpg")

        if not generate:
            return None

        self.load()

        l = level
        level = 1<<(self.levels-level)

        x0,y0,x1,y1 = (x*TILESIZE*level,y*TILESIZE*level,(x+1)*TILESIZE*level,(y+1)*TILESIZE*level)
        if x0 > self.img.size[0]:
            return None
        if y0 > self.img.size[1]:
            return None

        if x1 > self.img.size[0]:
            x1 = self.img.size[0]
        if y1 > self.img.size[1]:
            y1 = self.img.size[1]

        xl = (x1-x0) / level
        yl = (y1-y0) / level

        img = self.img.crop((x0,y0,x1,y1)).resize((xl,yl))
        tmpname = self.filepath+"/"+tileid+".jpg"
        img.save(tmpname)
        return tmpname

def send_imageproperties_xml(req):
    nid,data = splitpath(req.path)
    img = getImage(nid)
    req.write("""<IMAGE_PROPERTIES WIDTH="%d" HEIGHT="%d" NUMIMAGES="1" VERSION="1.8" TILESIZE="%d"/>""" % (img.width, img.height, TILESIZE))


def send_tile(req):
    nid, data = splitpath(req.path)
    img = getImage(nid)
    zoomlevels = 4

    if not req.path.endswith(".jpg"):
        print "invalid tile request", req.path
        return 404
    jpg = req.path[req.path.rindex("/")+1:-4]
    zoom,x,y = map(int, jpg.split("-"))

    tmpname = img.getTile(zoom, x, y)
    req.write(tmpname)
    return tmpname


