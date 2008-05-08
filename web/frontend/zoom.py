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
from utils.dicts import MaxSizeDict
IMGNAME = re.compile("/?tile/([^/]*)(/(.*))?$")

#
# TODO: We should cache image tiles in the node, not re-extract them for
#       every request
#

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

def getImage(nid):
    global cache
    if nid in cache:
        return cache[nid]

    node = tree.getNode(nid)
    for f in node.getFiles():
        if f.type == "image":
            img = ZoomImage(f.retrieveFile())
            cache[nid] = img
            return img

class ZoomImage:
    def __init__(self, filename):
        self.img = Image.open(filename)
        self.img.load()
        l = max(self.img.size)
        self.levels = 0
        while l > TILESIZE:
            l = l/2
            self.levels = self.levels + 1
        self.width,self.height = self.img.size

    def getTile(self, level, x, y):
        if level > self.levels:
            return None

        print level,x,y,self.levels
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
        tmpname = os.tmpnam()+".jpg"
        img.save(tmpname)
        return tmpname

def send_imageproperties_xml(req):
    nid,data = splitpath(req.path)
    img = getImage(nid)
    req.write("""<IMAGE_PROPERTIES WIDTH="%d" HEIGHT="%d" NUMIMAGES="1" VERSION="1.8" TILESIZE="%d"/>""" % (img.width, img.height, TILESIZE))

def send_tile(req):
    nid, data = splitpath(req.path)
    img = getImage(nid)

    zoomlevels = 4 # ?

    if not req.path.endswith(".jpg"):
        print "invalid tile request", req.path
        return 404
    jpg = req.path[req.path.rindex("/")+1:-4]
    zoom,x,y = map(int, jpg.split("-"))

    tmpname = img.getTile(zoom, x, y)
    if not tmpname:
        return 404
    r = req.sendFile(tmpname, "image/jpeg")
    os.unlink(tmpname)
    return r


