# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import httplib as _httplib
import os

import core.config as config
from core.database.postgres.file import File
from core.database.postgres.node import Node
from utils.utils import getMimeType, format_filesize
from core import webconfig
from sqlalchemy_continuum.utils import version_class

fileicons = {
    'directory': 'webtree/folder.svg',
    'application/pdf': 'pdf.svg',
    'image/jpeg': 'jpg.svg',
    'image/gif': 'gif.svg',
    'image/png': 'png.svg',
    'image/svg+xml': 'png.svg',
    'image/tiff': 'tiff.svg',
    'image/x-ms-bmp': 'bmp.svg',
    'application/postscript': 'ps.svg',
    'application/zip': 'zip.svg',
    'other': 'file.svg',
    'back': 'back.svg',
    'application/mspowerpoint': 'ppt.svg',
    'application/msword': 'msword.svg',
    'video/x-msvideo': 'avi.svg',
    'video/x-flv': 'mpg.svg',
    'video/quicktime': 'mpg.svg',
    'video/mp4': 'mpg.svg',
    'audio/x-wav': 'avi.svg',
    'audio/mpeg': 'mpg.svg',
    'text/x-bibtex': 'text.svg'
    }


def filebrowser(node, req):
    filesize = 0
    ret = list()
    if isinstance(node, Node):
        file_entity = File
    else:
        file_entity = version_class(File)

    paths = [t[0] for t in node.files.with_entities(file_entity.path).filter_by(filetype=u"attachment")]

    if len(paths) == 1 and os.path.isdir(config.get("paths.datadir") + paths[0]):
        # single file with no path
        path = paths[0]
    elif len(paths) > 0:
        # some single files
        files = []
        for path in paths:
            file = {}
            if not os.path.isdir(config.get("paths.datadir") + path):  # file
                file["mimetype"], file["type"] = getMimeType(config.get("paths.datadir") + path)
                icon = fileicons.get(file["mimetype"])
                if not icon:
                    icon = fileicons["other"]

                file["icon"] = icon
                file["path"] = path
                file["name"] = os.path.basename(path)
                if os.path.exists(config.get("paths.datadir") + path):
                    size = os.path.getsize(config.get("paths.datadir") + path)
                else:
                    size = 0
                file["size"] = format_filesize(size)
                filesize += int(size)
                files.append(file)

        return files, filesize
    else:
        path = ""

    if path == "":
        # no attachment directory -> test for single file

        for f in node.files.filter(~file_entity.filetype.in_(node.get_sys_filetypes())):
            file = {}
            file["mimetype"], file["type"] = getMimeType(f.getName())
            file["icon"] = fileicons.get(file["mimetype"], fileicons["other"])
            file["path"] = f.path
            file["name"] = f.base_name
            file["size"] = format_filesize(f.size)
            filesize += f.size
            ret.append(file)
        return ret, filesize

    if not path.endswith("/") and not req.params.get("path", "").startswith("/"):
        path += "/"
    path += req.params.get("path", "")

    if req.params.get("path", "") != "":
        file = {}
        file["type"] = "back"
        file["mimetype"] = "back"
        file["icon"] = fileicons.get(file["mimetype"], fileicons["other"])
        file["name"] = ".."
        file["path"] = req.params.get("path", "")
        file["req_path"] = req.params.get("path", "")[:req.params.get("path", "").rfind("/")]
        ret.append(file)

    for name in os.listdir(config.settings["paths.datadir"] + path + "/"):

        if name.endswith(".thumbnail"):
            continue
        file = {}

        file_path = os.path.join(config.settings["paths.datadir"] + path, name)
        if os.path.isdir(file_path):
            # directory
            file["type"] = "dir"
            file["mimetype"] = "directory"
        else:
            # file
            file["mimetype"], file["type"] = getMimeType(name)
            file["size"] = format_filesize(os.path.getsize(file_path))
            filesize += os.path.getsize(file_path)

        file["icon"] = fileicons.get(file["mimetype"], fileicons["other"])
        file["path"] = os.path.join(path, name)
        file["name"] = name
        file["req_path"] = req.params.get("path", "") + "/" + file["name"]
        ret.append(file)

    return ret, format_filesize(filesize)

""" format attachment browser """


def getAttachmentBrowser(node, req):
    f, s = filebrowser(node, req)
    html = webconfig.theme.render_macro(
        "popups.j2.jade", "attachmentbrowser",
        {"files": f, "sum_size": s, "id": req.params.get("id", ""), "path": req.params.get("path", "")})
    req.response.set_data(html)
    req.response.mimetype = "text/html"
    req.response.status_code = _httplib.OK
