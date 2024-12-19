# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging as _logging
import httplib as _httplib
import os

import operator as _operator

import core.config as config
from core.database.postgres.file import File
from core.database.postgres.node import Node
from utils.utils import getMimeType, format_filesize
from core import webconfig
from sqlalchemy_continuum.utils import version_class

_logg = _logging.getLogger(__name__)
fileicons = {
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
    if isinstance(node, Node):
        file_entity = File
    else:
        file_entity = version_class(File)

    basedir = config.get("paths.datadir")
    paths = node.files.with_entities(file_entity.path)
    paths = (
        paths.filter_by(filetype=u"attachment").all() or
        paths.filter(~file_entity.filetype.in_(node.get_sys_filetypes())).all()
        )
    files = []
    for path in map(_operator.itemgetter(0), paths):
        fullpath = os.path.join(basedir, path)
        mimetype = getMimeType(fullpath)
        if os.path.isfile(fullpath):
            size = os.path.getsize(fullpath)
        else:
            _logg.warning("node %s: attachment file missing on disk: %s", node.id, path)
            size = 0
        filesize += size
        files.append(dict(
            mimetype=mimetype[0],
            type=mimetype[1],
            size=format_filesize(size),
            icon=fileicons.get(mimetype[0], fileicons["other"]),
            name=os.path.basename(path),
            path=path,
            ))

    return files, filesize

""" format attachment browser """


def getAttachmentBrowser(node, req):
    f, s = filebrowser(node, req)
    html = webconfig.theme.render_macro(
        "popups.j2.jade",
        "attachmentbrowser",
        dict(files=f, sum_size=s, id=req.values.get("id", ""))
        )
    req.response.set_data(html)
    req.response.mimetype = "text/html"
    req.response.status_code = _httplib.OK
