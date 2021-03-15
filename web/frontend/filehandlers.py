# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division

from functools import partial
import logging
import os
import glob

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_continuum.utils import version_class
from urllib import quote
from core import db
from core import Node, File
import core.config as config
from core import request_handler as _request_handler
from core.archive import get_archive_for_node
from contenttypes import Container
from contenttypes import Content
from contenttypes.data import Data
from schema.schema import existMetaField
from web.frontend.filehelpers import get_node_or_version
from web.frontend.filehelpers import node_id_from_req_path
from web.frontend.filehelpers import preference_sorted_image_mimetypes
from web.frontend.filehelpers import split_image_path
from web.frontend.filehelpers import splitpath
from web.frontend.filehelpers import version_id_from_req
from utils import userinput
import utils.utils
from utils.utils import getMimeType, clean_path, get_filesize
import tempfile
from utils.compat import iterkeys
from core import httpstatus


logg = logging.getLogger(__name__)
q = db.query
_webroots = []


def _send_thumbnail(thumb_type, req):
    try:
        nid = node_id_from_req_path(req.mediatum_contextfree_path)
    except ValueError:
        req.response.status_code = 400
        return 400


    version_id = version_id_from_req(req.args)

    node_or_version = get_node_or_version(nid, version_id, Data)

    if not node_or_version.has_read_access():
        req.response.status_code = 404
        return 404

    FileVersion = version_class(File)
    if version_id:
        version = node_or_version
        files = version.files.filter_by(filetype=thumb_type, transaction_id=version.transaction_id).all()
        if not files:
            # files may be None if in this version only metadata changed
            # then try previous transaction_ids
            files = version.files.filter(FileVersion.filetype==thumb_type, FileVersion.transaction_id<=version.transaction_id). \
                order_by(FileVersion.transaction_id.desc())
        for f in files:
            if f.exists:
                return _request_handler.sendFile(req, f.abspath, f.mimetype)

        ntype, schema = version.type, version.schema
    else:
        # no version id given
        # XXX: better to use scalar(), but we must ensure that we have no dupes first
        node = node_or_version
        for f in node.files.filter_by(filetype=thumb_type):
            if f.exists:
                return _request_handler.sendFile(req, f.abspath, f.mimetype)

        try:
            ntype, schema = node.type, node.schema
        except NoResultFound:
            req.response.status_code = 404
            return 404

    # looking in all img filestores for default thumb for this
    # a) node type and schema, or
    # b) schema, or
    # c) node type
    img_filestorepaths = _request_handler.getFileStorePaths("/img/")

    for pattern_fmt in (
            "default_thumb_{ntype}_{schema}.*",
            "default_thumb_{schema}.*",
            "default_thumb_{ntype}.*",
    ):

        for p in img_filestorepaths:
            fps = glob.glob(os.path.join(p, pattern_fmt.format(schema=schema, ntype=ntype)))
            if fps:
                thumb_path, = fps  # implicit: raises ValueError if not len(fps)==1
                thumb_mimetype, thumb_type = utils.utils.getMimeType(thumb_path)
                logg.debug("serving default thumb for node '%s': %s", node, thumb_path)
                return _request_handler.sendFile(req, thumb_path, thumb_mimetype, force=1)


    return _request_handler.sendFile(req, config.basedir + "/web/img/questionmark.png", "image/png", force=1)


send_thumbnail = partial(_send_thumbnail, u"thumb")
send_thumbnail2 = partial(_send_thumbnail, u"presentation")


def send_doc(req):
    try:
        nid = node_id_from_req_path(req.mediatum_contextfree_path)
    except ValueError:
        req.response.status_code = 400
        return 400

    version_id = version_id_from_req(req.args)
    node = get_node_or_version(nid, version_id, Content)

    if node is None or not node.has_data_access():
        req.response.status_code = 404
        return 404

    fileobj = None
    file_query = node.files.filter_by(filetype=u'document')
    # if version_id == u"published":
    if version_id:
        file_query = file_query.filter_by(transaction_id=node.transaction_id)
        fileobj = file_query.scalar()
        # fileobj may be None if in this version only metadata changed
        # then try previous transaction_ids
        if not fileobj:
            FileVersion = version_class(File)
            # this a long lasting query
            file_query = node.files.filter_by(filetype=u'document')
            fileobj = file_query.filter(FileVersion.transaction_id <= node.transaction_id).\
                order_by(FileVersion.transaction_id.desc()).first()

    if not fileobj:
        fileobj = file_query.scalar()

    return _request_handler.sendFile(req, fileobj.abspath, fileobj.mimetype) if fileobj else 404


def send_image(req):
    try:
        nid, file_ext = split_image_path(req.mediatum_contextfree_path)
    except ValueError:
        req.response.status_code = 404
        return 400

    version_id = version_id_from_req(req.args)

    node = get_node_or_version(nid, version_id, Content)

    # XXX: should be has_data_access instead, see #1135
    if node is None or not node.has_read_access():
        req.response.status_code = 404
        return 404

    image_files_by_mimetype = {f.mimetype: f for f in node.files.filter_by(filetype=u"image")}

    if not image_files_by_mimetype:
        # no image files? forget it...
        req.response.status_code = 404
        return 404

    def _send(fileobj):
        return _request_handler.sendFile(req, fileobj.abspath, fileobj.mimetype)

    client_mimetype = None

    if file_ext:
        # client wants a specific mimetype
        client_mimetype = node.MIMETYPE_FOR_EXTENSION.get(file_ext)
        if not client_mimetype:
            req.response.status_code = httpstatus.HTTP_NOT_ACCEPTABLE
            return httpstatus.HTTP_NOT_ACCEPTABLE

        image_file = image_files_by_mimetype.get(client_mimetype)
        if image_file:
            return _send(image_file)
        else:
            req.response.status_code = httpstatus.HTTP_NOT_ACCEPTABLE
            return httpstatus.HTTP_NOT_ACCEPTABLE

    # figure out what we want to send, in that order:
    server_preferred_mimetypes = preference_sorted_image_mimetypes(node, iterkeys(image_files_by_mimetype))

    if req.accept_mimetypes:
        client_mimetype = req.accept_mimetypes.best_match(server_preferred_mimetypes)
        if client_mimetype:
            # file for mimetype must exist here
            image_file = image_files_by_mimetype[client_mimetype]
            return _send(image_file)
        else:
            req.response.status_code = httpstatus.HTTP_NOT_ACCEPTABLE
            return httpstatus.HTTP_NOT_ACCEPTABLE
    else:
        # client doesn't have any preferences, send our choice
        return _send(image_files_by_mimetype[server_preferred_mimetypes[0]])

    req.response.status_code = 404
    return 404


def send_original_file(req):
    try:
        nid = node_id_from_req_path(req.mediatum_contextfree_path)
    except ValueError:
        req.response.status_code = 400
        return 400

    version_id = version_id_from_req(req.args)

    node = get_node_or_version(nid, version_id, Data)

    if node is None or not node.has_data_access():
        req.response.status_code = 404
        return 404

    original_filetype = node.get_original_filetype()
    original_file = node.files.filter_by(filetype=original_filetype).scalar()
    if original_file is not None:
        return _request_handler.sendFile(req, original_file.abspath, original_file.mimetype)

    return 404


def send_file(req):
    parts = splitpath(req.mediatum_contextfree_path)
    if len(parts) != 2:
        req.response.status_code = 400
        return 400

    nidstr, filename = parts
    assert not nidstr.endswith("_transfer.zip")

    nid = userinput.string_to_int(nidstr)
    if nid is None:
        req.response.status_code = 400
        return 400

    version_id = version_id_from_req(req.args)

    node = get_node_or_version(nid, version_id)

    if (node is None
            or isinstance(node, Container) and not node.has_read_access()
            or isinstance(node, Content) and not node.has_data_access()):
        req.response.status_code = 404
        return 404

    def _send_attachment(filepath, mimetype):
        file_ext = os.path.splitext(filepath)[1]
        if node.schema and existMetaField(node.schema, u'nodename'):
            display_file_name = u'{}{}'.format(os.path.splitext(os.path.basename(node.name))[0], file_ext)
        else:
            display_file_name = filename
        try:
            display_file_name.encode('ascii')
        except UnicodeEncodeError:
            req.response.headers["Content-Disposition"] = u'attachment; filename="{0}"; filename*=UTF-8\'\'{0}'. \
                format(quote(display_file_name.encode('utf8')))
        else:
            req.response.headers["Content-Disposition"] = u'attachment; filename="{}"'.format(display_file_name)
        return _request_handler.sendFile(req, filepath, mimetype)

    assert filename is not None

    # try full filename
    for f in node.files:
        if f.base_name == filename:
            return _send_attachment(f.abspath, f.mimetype)

    archive = get_archive_for_node(node)
    if archive:
        filepath = archive.get_local_filepath(node)
        mimetype, _ = getMimeType(filepath)
        return _send_attachment(filepath, mimetype)

    else:
        # try only extension
        file_ext = os.path.splitext(filename)[1]
        for f in node.files:
            if os.path.splitext(f.base_name)[1] == file_ext and f.filetype in [u'document', u'original', u'mp3']:
                logg.warn("serving file %s for node %s only by matched extension", f.path, node.id)
                return _send_attachment(f.abspath, f.mimetype)

    req.response.status_code = 404
    return 404


def send_attfile(req):
    """send single attachment file to user"""
    parts = req.mediatum_contextfree_path[9:].split('/')

    if len(parts) < 2:
        req.response.status_code = 404
        return 400

    nid = userinput.string_to_int(parts[0])
    if nid is None:
        req.response.status_code = 404
        return 400

    version_id = version_id_from_req(req.args)

    node = get_node_or_version(nid, version_id, Data)

    # XXX: why do we want to send attachments from containers?
    if (node is None
            or isinstance(node, Container) and not node.has_read_access()
            or isinstance(node, Content) and not node.has_data_access()):
        req.response.status_code = 404
        return 404

    paths = ["/".join(parts[1:]), "/".join(parts[1:-1])]
    fileobjs = [fo for fo in node.files if fo.path in paths]

    if not fileobjs:
        req.response.status_code = 404
        return 404

    fileobj = fileobjs[0]

    if fileobj.mimetype == u'inode/directory':
        # files in attachment directory cannot be found in node.files
        # so send file directly as it was made in mysql
        filename = clean_path("/".join(parts[1:]))
        path = os.path.join(config.get("paths.datadir"), filename)
        mime, type = getMimeType(filename)
        if (get_filesize(filename) > 16 * 1048576):
            req.response.headers["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)

        return _request_handler.sendFile(req, path, mime)

    if (fileobj.size > 16 * 1048576):
        req.response.headers["Content-Disposition"] = u'attachment; filename="{}"'.format(fileobj.base_name).encode('utf8')

    return _request_handler.sendFile(req, fileobj.abspath, fileobj.mimetype)


def fetch_archived(req):
    try:
        nid = node_id_from_req_path(req.mediatum_contextfree_path)
    except ValueError:
        req.response.status_code = 400
        return 400

    node = q(Content).get(nid)

    archive = get_archive_for_node(node)
    if archive:
        try:
            archive.fetch_file_from_archive(node)
        except:
            logg.exception("exception in fetch_file_from_archive for archive %s", archive.archive_type)
            msg = "fetch archive for node failed"
            req.response.status_code = 500
            req.response.set_data(msg)
        else:
            req.response.set_data("done")
    else:
        msg = "archive for node not found"
        req.response.status_code = 400
        req.response.set_data(msg)
        logg.warn(msg)

    db.session.commit()


def send_from_webroot(req):
    for webroot_dir in _webroots:
        filepath = os.path.join(config.basedir, webroot_dir, req.mediatum_contextfree_path.strip("/"))
        if os.path.isfile(filepath):
            return _request_handler.sendFile(req, filepath, getMimeType(filepath)[0])

    return 404

### redirects for legacy handlers

def redirect_images(req):
    req.response.location = "/image" + req.full_path[7:]
    req.response.status_code = 301
    return 301


def add_web_root(webroot):
    if not (os.path.isdir(webroot) and os.path.isabs(webroot)):
        raise ValueError('Directory is not an absolute path {}'.format(webroot))
    _webroots.append(webroot)
