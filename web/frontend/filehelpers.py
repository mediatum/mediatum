# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from __future__ import division

import logging
import os
import re
import zipfile
import utils.utils as _utils_utils
from core import config, db, Node
from contenttypes import Content
from utils.utils import getMimeType, get_filesize, suppress
from utils import userinput
from utils.compat import text_type
from core.request_handler import sendFile as _sendFile


FILEHANDLER_RE = re.compile("/?(attachment|doc|images|thumbs|thumb2|file|download|archive)/([^/]*)(/(.*))?$")
IMAGE_HANDLER_RE = re.compile("^/?image/(\d+)(?:\.(.{1,5}))?$")

logg = logging.getLogger(__name__)

q = db.query


def split_image_path(path):
    if not isinstance(path, text_type):
        path = path.decode("utf8")
    
    m  = IMAGE_HANDLER_RE.match(path)
    if not m:
        raise ValueError("invalid image path")

    node_id, ext = m.groups()
    return node_id, ext


def splitpath(path):
    if not isinstance(path, text_type):
        path = path.decode("utf8")
    
    m = FILEHANDLER_RE.match(path)
    if m is None:
        return path
    try:
        return m.group(2), m.group(4)
    except:
        return m.group(2), None


def node_id_from_req_path(path):
    parts = splitpath(path)

    if not parts:
        raise ValueError("invalid node ID path '{}'".format(path))

    nid = userinput.string_to_int(parts[0])

    if nid is None:
        raise ValueError("path contains an invalid node ID: '{}'".format(path))

    return nid


def version_id_from_req(req_args):
    version = req_args.get("v")
    if version != u"published":
        return req_args.get("v", type=int)
    return version


def get_node_or_version(nid, version_id=None, nodeclass=Node):
    if nid is None:
        return None

    node = q(nodeclass).get(nid)

    version = None

    if version_id:
        if version_id == u"published":
            version = node.get_published_version()
        else:
            version = node.get_tagged_version(unicode(version_id))

    return version if version is not None else node


def sendBibFile(req, path):
    req.response.headers['Content-Disposition'] = "attachment; filename=export.bib"
    _sendFile(req, path, getMimeType(path))
    if os.sep == '/':  # Unix?
        os.unlink(path)  # unlinking files while still reading them only works on Unix/Linux


def get_all_file_paths(basedir):
    res = []
    for dirpath, dirnames, filenames in os.walk(basedir):
        for fn in filenames:
            res.append(os.path.join(dirpath, fn))
    return res


def build_filelist(node):
    "build file list for generation of xmetadissplus xml"
    if not (isinstance(node, Content) and node.has_data_access()):
        return []
    files_written = 0
    result_list = []

    # limit transfer.zip to one node
    for n in [node]:
        if n.isActiveVersion():
            for fn in n.files:
                if fn.filetype in ['document', 'zip', 'attachment', 'other']:
                    fullpath = fn.abspath
                    if os.path.isfile(fullpath) and os.path.exists(fullpath):
                        dirname, filename = os.path.split(fullpath)
                        result_list.append([filename, fn.getSize()])
                        files_written += 1
                    if os.path.isdir(fullpath):
                        for f in get_all_file_paths(fullpath):
                            dirname, filename = os.path.split(f)
                            result_list.append([filename, get_filesize(f)])
                            files_written += 1

    return result_list


def get_transfer_url(n):
    "get transfer url for transfer.zip archive of appended files (for example for oai format xmetadissplus)"
    filecount = len(build_filelist(n))
    if filecount < 2:
        transfer_filename = ustr(n.id) + ".pdf"
        transferurl = u"http://{}/doc/{}/{}".format(config.get("host.name"), n.id, transfer_filename)
    else:
        transfer_filename = ustr(n.id) + "_transfer.zip"
        transferurl = u"http://{}/file/{}".format(config.get("host.name"), transfer_filename)

    return transferurl


def preference_sorted_image_mimetypes(image, mimetypes):
    preferred_mimetype = image.system_attrs.get("preferred_mimetype")
    original_file = image.files.filter_by(filetype=u"original").scalar()

    def _score(mimetype):
        if mimetype == preferred_mimetype:
            return 3
        if mimetype == "image/png":
            # because png is cool (and supported by all reasonable browsers) ;)
            return 2
        if original_file is not None and mimetype == original_file.mimetype:
            return 1
        return 0

    return sorted(mimetypes, key=_score, reverse=True)
