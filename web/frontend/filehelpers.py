# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import logging
import os
import re
import random
import zipfile
from core import config, db, Node
from contenttypes import Content
from utils.utils import getMimeType, get_filesize
from utils import userinput
from utils.compat import text_type


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


def node_id_from_req_path(req):
    parts = splitpath(req.path)

    if not parts:
        raise ValueError("invalid node ID path '{}'".format(req.path))

    nid = userinput.string_to_int(parts[0])

    if nid is None:
        raise ValueError("path contains an invalid node ID: '{}'".format(req.path))

    return nid


def version_id_from_req(req):
    return req.args.get("v", type=int)


def get_node_or_version(nid, version_id=None, nodeclass=Node):
    if nid is None:
        return None

    node = q(nodeclass).get(nid)

    version = None

    if version_id:
        version = node.get_tagged_version(unicode(version_id))

    return version if version is not None else node


def sendZipFile(req, path):
    tempfile = os.path.join(config.get("paths.tempdir"), unicode(random.random())) + ".zip"
    zip = zipfile.ZipFile(tempfile, "w")
    zip.debug = 3

    def r(p):
        if os.path.isdir(os.path.join(path, p)):
            for file in os.listdir(os.path.join(path, p)):
                r(os.path.join(p, file))
        else:
            while len(p) > 0 and p[0] == "/":
                p = p[1:]
            try:
                zip.write(os.path.join(path, p), p)
            except:
                pass

    r("/")
    zip.close()
    req.reply_headers['Content-Disposition'] = "attachment; filename=shoppingbag.zip"
    req.sendFile(tempfile, "application/zip")
    if os.sep == '/':  # Unix?
        os.unlink(tempfile)  # unlinking files while still reading them only works on Unix/Linux


def sendBibFile(req, path):
    req.reply_headers['Content-Disposition'] = "attachment; filename=export.bib"
    req.sendFile(path, getMimeType(path))
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


def build_transferzip(dest_file, node):
    nid = node.id

    def _add_files_to_zip(zfile, node):
        files_written = 0
        for fo in node.files:
            if fo.filetype in ['document', 'zip', 'attachment', 'other']:
                fullpath = fo.abspath
                if os.path.isfile(fullpath) and os.path.exists(fullpath):
                    filename = fo.base_name
                    logg.debug("adding to zip: %s as %s", fullpath, filename)
                    zfile.write(fullpath, filename)
                    files_written += 1
                if os.path.isdir(fullpath):
                    for filepath in get_all_file_paths(fullpath):
                        relpath = filepath.replace(fullpath, "")
                        logg.debug("adding from directory %s to zip as %s", fullpath, relpath)
                        zfile.write(filepath, relpath)
                        files_written += 1
        return files_written

    count_files_written = 0
    logg.info("builing transfer zip for node %s", nid)

    with zipfile.ZipFile(dest_file, "w", zipfile.ZIP_DEFLATED) as zfile:
        if isinstance(node, Content) and node.has_data_access():
            count_files_written = _add_files_to_zip(zfile, node)

    return count_files_written


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
