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
import logging
import re
import os
from PIL import Image as PILImage
import zipfile
import random
from core import db, File
import core.config as config
from utils.lrucache import lru_cache


logg = logging.getLogger(__name__)
IMGNAME = re.compile("/?tile/([^/]*)(/(.*))?$")

store = 1  # keep tiles?


q = db.query

def splitpath(path):
    m = IMGNAME.match(path)
    if m is None:
        return path
    try:
        return m.group(1), m.group(3)
    except:
        return m.group(1), None

TILESIZE = 256


@lru_cache(maxsize=16)
def getImage(nid, preprocess=0):
    from contenttypes import Image
    node = q(Image).get(nid)
    img = ZoomImage(node, preprocess)
    return img


class ZoomImage:

    def __init__(self, node, preprocess=0):
        self.node = node
        self.width = int(self.node.get("width"))
        self.height = int(self.node.get("height"))
        self.levels = int(self.node.system_attrs.get("zoom_levels", 0))
        self.img = None
        self.z_file = None
        self.filepath = None
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

        self.img = PILImage.open(filename)
        tmpjpg = config.get("paths.datadir") + "tmp/img" + ustr(random.random()) + ".jpg"
        if self.img.mode == "CMYK" and (filename.endswith("jpg") or filename.endswith("jpeg")) or self.img.mode in ["P", "L"]:
            os.system("convert -quality 100 -draw \"rectangle 0,0 1,1\" %s %s" % (filename, tmpjpg))
            self.img = PILImage.open(tmpjpg)
        self.img.load()
        l = max(self.img.size)
        self.levels = 0
        while l > TILESIZE:
            l = l / 2
            self.levels = self.levels + 1
        self.width, self.height = self.img.size
        self.node.system_attrs["zoom_levels"] = self.levels
        if os.path.exists(tmpjpg):
            os.unlink(tmpjpg)

    def preprocess(self):
        names = []
        for level in range(self.levels + 1):
            t = (TILESIZE << (self.levels - level))
            for x in range((self.width + (t - 1)) / t):
                for y in range((self.height + (t - 1)) / t):
                    names.append(self.getTile(level, x, y, 1))

        # open the zip file for writing, and write stuff to it
        file = zipfile.ZipFile(self.filepath + u"/zoom{}.zip".format(self.node.id), "w")
        for name in names:
            file.write(name, os.path.basename(name), zipfile.ZIP_DEFLATED)
            os.unlink(name)
        file.close()
        l = config.get("paths.datadir")
        file_obj = File(path=self.filepath[len(l):] + u"/zoom{}.zip".format(self.node.id), mimetype="application/zip", filetype="zoom")
        self.node.files.append(file_obj)
        db.session.commit()

    def getTile(self, level, x, y, generate=0):
        if level > self.levels:
            return None

        tileid = "tile-%d-%d-%d" % (level, x, y)

        if not self.z_file:
            for f in self.node.getFiles():
                if f.type == "zoom" and os.path.exists(self.filepath + "/" + f.getName()):
                    self.z_file = zipfile.ZipFile(self.filepath + "/" + f.getName(), "r")
                    break
        if self.z_file:
            return self.z_file.read(tileid + ".jpg")

        if not generate:
            return None

        l = level
        level = 1 << (self.levels - level)

        x0, y0, x1, y1 = (x * TILESIZE * level, y * TILESIZE * level, (x + 1) * TILESIZE * level, (y + 1) * TILESIZE * level)
        if x0 > self.img.size[0]:
            return None
        if y0 > self.img.size[1]:
            return None

        if x1 > self.img.size[0]:
            x1 = self.img.size[0]
        if y1 > self.img.size[1]:
            y1 = self.img.size[1]

        xl = (x1 - x0) / level
        yl = (y1 - y0) / level

        img = self.img.crop((x0, y0, x1, y1)).resize((xl, yl))
        tmpname = self.filepath + "/" + tileid + ".jpg"
        try:
            img.save(tmpname)
        except:
            pass
        return tmpname


def send_imageproperties_xml(req):
    nid, data = splitpath(req.path)
    img = getImage(nid)
    req.write("""<IMAGE_PROPERTIES WIDTH="%d" HEIGHT="%d" NUMIMAGES="1" VERSION="1.8" TILESIZE="%d"/>""" %
              (img.width, img.height, TILESIZE))


def send_tile(req):
    nid, data = splitpath(req.path)
    img = getImage(nid)

    if not req.path.endswith(".jpg"):
        logg.warn("invalid tile request %s", req.path)
        return 404
    jpg = req.path[req.path.rindex("/") + 1:-4]
    zoom, x, y = map(int, jpg.split("-"))

    try:
        tmpname = img.getTile(zoom, x, y)
        req.write(tmpname)
        return 200
    except:
        logg.exception("exception in send_tile")
        return 404
    return tmpname
