"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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
import core.config as config

from utils.utils import getMimeType, format_filesize
from core.styles import theme

fileicons = {'directory': 'mmicon_dir.gif',
             'application/pdf': 'mmicon_pdf.gif',
             'image/jpeg': 'mmicon_jpg.gif',
             'image/gif': 'mmicon_gif.gif',
             'image/png': 'mmicon_png.gif',
             'image/svg+xml': 'mmicon_png.gif',
             'image/tiff': 'mmicon_tiff.gif',
             'image/x-ms-bmp': 'mmicon_bmp.gif',
             'application/postscript': 'mmicon_ps.gif',
             'application/zip': 'mmicon_zip.gif',
             'other': 'mmicon_file.gif',
             'back': 'mmicon_back.gif',
             'application/mspowerpoint': 'mmicon_ppt.gif',
             'application/msword': 'mmicon_doc.gif',
             'video/x-msvideo': 'mmicon_avi.gif',
             'video/x-flv': 'mmicon_mpeg.gif',
             'audio/x-wav': 'mmicon_avi.gif',
             'audio/mpeg': 'mmicon_mpeg.gif',
             'text/x-bibtex': 'mmicon_txt.gif'}


def filebrowser(node, req):
    filesize = 0
    ret = list()
    paths = []
    for f in node.getFiles():
        if f.getType() == "attachment":
            paths.append(f._path)
            # break

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
                file["icon"] = fileicons[file["mimetype"]]
                file["path"] = path
                file["name"] = f.getName()
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
        file = {}
        for f in node.getFiles():
            if f.getType() not in node.getSysFiles():
                file["mimetype"], file["type"] = getMimeType(f.getName())
                file["icon"] = fileicons[file["mimetype"]]
                file["path"] = f._path
                file["name"] = f.getName()
                size = f.getSize() or 0
                file["size"] = format_filesize(size)
                filesize += f.getSize()
                ret.append(file)
        return ret, filesize

    if not path.endswith("/") and not req.params.get("path", "").startswith("/"):
        path += "/"
    path += req.params.get("path", "")

    if req.params.get("path", "") != "":
        file = {}
        file["type"] = "back"
        file["mimetype"] = "back"
        file["icon"] = fileicons[file["mimetype"]]
        file["name"] = ".."
        file["path"] = req.params.get("path", "")
        file["req_path"] = req.params.get("path", "")[:req.params.get("path", "").rfind("/")]
        ret.append(file)

    for name in os.listdir(config.settings["paths.datadir"] + path + "/"):

        if name.endswith(".thumb") or name.endswith(".thumb2"):
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

        file["icon"] = fileicons[file["mimetype"]]
        file["path"] = os.path.join(path, name)
        file["name"] = name
        file["req_path"] = req.params.get("path", "") + "/" + file["name"]
        ret.append(file)

    return ret, format_filesize(filesize)

""" format attachment browser """


def getAttachmentBrowser(node, req):
    f, s = filebrowser(node, req)
    req.writeTAL(theme.getTemplate("popups.html"), {"files": f, "sum_size": s, "id": req.params.get(
        "id", ""), "path": req.params.get("path", "")}, macro="attachmentbrowser")
