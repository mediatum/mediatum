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
from __future__ import division

import logging
import re
import zipfile
import backports.functools_lru_cache as _backports_functools_lru_cache
import core.httpstatus as _httpstatus
from core import db, Node, File, NodeToFile
from contenttypes import Image


logg = logging.getLogger(__name__)
IMGNAME = re.compile("/?tile/([^/]*)(/(.*))?$")

store = True  # keep tiles?

q = db.query


def splitpath(path):
    m = IMGNAME.match(path)
    if m is None:
        return path
    try:
        return m.group(1), m.group(3)
    except:
        return m.group(1), None


@_backports_functools_lru_cache.lru_cache(maxsize=100000)
def get_cached_image_zoom_data(nid):
    return ImageZoomData(nid)


class ImageZoomData(object):

    def __init__(self, node_id):
        self.node_id = node_id
        node = q(Image).get(node_id)
        if node is None:
            raise ValueError("requested node does not exist or is not an image node: " + str(node_id))

        self.width = int(node.get("origwidth") or node.get("width", 0))

        if not self.width:
            logg.warning("original width for image %s is zero or missing!", self.node_id)

        self.height = int(node.get("origheight") or node.get("width", 0))

        if not self.height:
            logg.warning("original width for image %s is zero or missing!", self.node_id)

        zoom_file = q(File).filter_by(filetype=u"zoom").join(NodeToFile).join(Image).filter_by(id=self.node_id).scalar()
        
        self.zoom_filepath = None

        if zoom_file is None:
            logg.warning("no zoom file entry exists for image node %s, cannot provide tiles!", self.node_id)
            return

        if not zoom_file.exists:
            logg.warning(
                "zoom file for image node %s is missing on disk, cannot provide tiles! (should be at %s)",
                self.node_id,
                zoom_file.path,
            )
            return

        self.zoom_filepath = zoom_file.abspath

    def get_tile(self, level, x, y):
        if not self.zoom_filepath:
            logg.warning("zoom file missing for node %s, cannot provide zoom tile!", self.node_id)
            return
        
        tileid = "tile-%d-%d-%d" % (level, x, y)
        z_file = zipfile.ZipFile(self.zoom_filepath, "r")
        return z_file.read(tileid + ".jpg")


def send_imageproperties_xml(req):
    nid, data = splitpath(req.mediatum_contextfree_path)

    if not Node.req_has_access_to_node_id(nid, u"read", req):
        req.response.status_code = 404
        return 404

    img = get_cached_image_zoom_data(nid)
    req.response.set_data(req.response.get_data() + """<IMAGE_PROPERTIES WIDTH="%d" HEIGHT="%d" NUMIMAGES="1" VERSION="1.8" TILESIZE="%d"/>""" % (
        img.width, img.height, Image.ZOOM_TILESIZE))
    req.response.status_code = _httpstatus.HTTP_OK


def send_tile(req):
    nid, data = splitpath(req.mediatum_contextfree_path)

    if not Node.req_has_access_to_node_id(nid, u"read", req):
        req.response.status_code = 404
        return 404

    if not req.mediatum_contextfree_path.endswith(".jpg"):
        logg.error("invalid tile request %s", req.mediatum_contextfree_path)
        req.response.status_code = 404
        return 404

    jpg = req.mediatum_contextfree_path[req.mediatum_contextfree_path.rindex("/") + 1:-4]
    zoom, x, y = map(int, jpg.split("-"))

    try:
        img = get_cached_image_zoom_data(nid)
        tile = img.get_tile(zoom, x, y)

        if tile is None:
            req.response.status_code = 404
            return 404

        req.response.set_data(req.response.get_data() + tile)
        req.response.status_code = _httpstatus.HTTP_OK
    except:
        logg.exception("exception in send_tile")
        req.response.status_code = 500
        return 500
