# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from functools import partial
import logging
import os
import glob

from sqlalchemy.orm.exc import NoResultFound
from core import db
from core import Node, File
import core.config as config
import core.athana as athana
from core.archive import get_archive_for_node
from contenttypes import Container
from contenttypes import Content
from contenttypes.data import Data
from schema.schema import existMetaField
from web.frontend.filehelpers import sendZipFile, splitpath, build_transferzip, node_id_from_req_path, split_image_path,\
    preference_sorted_image_mimetypes, version_id_from_req, get_node_or_version
from utils import userinput
import utils.utils
from utils.utils import getMimeType
import tempfile
from utils.compat import iterkeys
from core.transition import httpstatus


logg = logging.getLogger(__name__)
q = db.query


def _send_thumbnail(thumb_type, req):
    try:
        nid = node_id_from_req_path(req)
    except ValueError:
        return 400


    version_id = version_id_from_req(req)

    node_or_version = get_node_or_version(nid, version_id, Data)

    if not node_or_version.has_read_access():
        return 404

    if version_id:
        version = node_or_version
        for f in version.files.filter_by(filetype=thumb_type, transaction_id=version.transaction_id):
            if f.exists:
                return req.sendFile(f.abspath, f.mimetype)

        ntype, schema = version.type, version.schema
    else:
        # no version id given
        # XXX: better to use scalar(), but we must ensure that we have no dupes first
        node = node_or_version
        for f in node.files.filter_by(filetype=thumb_type):
            if f.exists:
                return req.sendFile(f.abspath, f.mimetype)

        try:
            ntype, schema = node.type, node.schema
        except NoResultFound:
            return 404

    for p in athana.getFileStorePaths("/img/"):
        for test in ["default_thumb_%s_%s.*" % (ntype, schema),
                     "default_thumb_%s.*" % schema,
                     "default_thumb_%s.*" % ntype]:
            fps = glob.glob(os.path.join(p, test))
            if fps:
                thumb_mimetype, thumb_type = utils.utils.getMimeType(fps[0])
                return req.sendFile(fps[0], thumb_mimetype, force=1)

    return req.sendFile(config.basedir + "/web/img/questionmark.png", "image/png", force=1)


send_thumbnail = partial(_send_thumbnail, u"thumb")
send_thumbnail2 = partial(_send_thumbnail, u"presentation")


def _send_file_with_type(filetype, mimetype, req):
    try:
        nid = node_id_from_req_path(req)
    except ValueError:
        return 400

    version_id = version_id_from_req(req)
    node = get_node_or_version(nid, version_id, Content)

    if node is None or not node.has_data_access():
        return 404

    file_query = node.files.filter_by(filetype=filetype)
    if version_id:
        file_query = file_query.filter_by(transaction_id=node.transaction_id)
    if mimetype:
        file_query = file_query.filter_by(mimetype=mimetype)

    fileobj = file_query.scalar()
    if fileobj is not None:
        return req.sendFile(fileobj.abspath, fileobj.mimetype)

    return 404


send_doc = partial(_send_file_with_type, u"document", None)


def send_image(req):
    try:
        nid, file_ext = split_image_path(req.path)
    except ValueError:
        return 400

    version_id = version_id_from_req(req)

    node = get_node_or_version(nid, version_id, Content)

    # XXX: should be has_data_access instead, see #1135
    if node is None or not node.has_read_access():
        return 404

    image_files_by_mimetype = {f.mimetype: f for f in node.files.filter_by(filetype=u"image")}

    if not image_files_by_mimetype:
        # no image files? forget it...
        return 404

    def _send(fileobj):
        return req.sendFile(fileobj.abspath, fileobj.mimetype)

    client_mimetype = None

    if file_ext:
        # client wants a specific mimetype
        client_mimetype = node.MIMETYPE_FOR_EXTENSION.get(file_ext)
        if not client_mimetype:
            return httpstatus.HTTP_NOT_ACCEPTABLE

        image_file = image_files_by_mimetype.get(client_mimetype)
        if image_file:
            return _send(image_file)
        else:
            return httpstatus.HTTP_NOT_ACCEPTABLE

    # figure out what we want to send, in that order:
    server_preferred_mimetypes = preference_sorted_image_mimetypes(node, iterkeys(image_files_by_mimetype))

    accept_mimetypes = req.accept_mimetypes

    if accept_mimetypes:
        client_mimetype = req.accept_mimetypes.best_match(server_preferred_mimetypes)
        if client_mimetype:
            # file for mimetype must exist here
            image_file = image_files_by_mimetype[client_mimetype]
            return _send(image_file)
        else:
            return httpstatus.HTTP_NOT_ACCEPTABLE
    else:
        # client doesn't have any preferences, send our choice
        return _send(image_files_by_mimetype[server_preferred_mimetypes[0]])

    return 404


def send_original_file(req):
    try:
        nid = node_id_from_req_path(req)
    except ValueError:
        return 400

    version_id = version_id_from_req(req)

    node = get_node_or_version(nid, version_id, Data)

    if node is None or not node.has_data_access():
        return 404

    original_filetype = node.get_original_filetype()
    original_file = node.files.filter_by(filetype=original_filetype).scalar()
    if original_file is not None:
        return req.sendFile(original_file.abspath, original_file.mimetype)

    return 404


def send_file(req):
    parts = splitpath(req.path)
    if len(parts) != 2:
        return 400

    nidstr, filename = parts
    if nidstr.endswith("_transfer.zip"):
        nidstr = nidstr[:-13]

    nid = userinput.string_to_int(nidstr)
    if nid is None:
        return 400

    version_id = version_id_from_req(req)

    node = get_node_or_version(nid, version_id)

    if (node is None
            or isinstance(node, Container) and not node.has_read_access()
            or isinstance(node, Content) and not node.has_data_access()):
        return 404

    def _send_attachment(filepath, mimetype):
        file_ext = os.path.splitext(filepath)[1]
        if existMetaField(node.schema, u'nodename'):
            display_file_name = u'{}{}'.format(os.path.splitext(os.path.basename(node.name))[0], file_ext)
        else:
            display_file_name = filename
        req.reply_headers["Content-Disposition"] = u'attachment; filename="{}"'.format(display_file_name)
        return req.sendFile(filepath, mimetype)

    if filename is None:
        # build zip-file and return it
        with tempfile.NamedTemporaryFile() as tmpfile:
            files_written = build_transferzip(tmpfile, node)
            if files_written == 0:
                return 404
            return req.sendFile(tmpfile.name, "application/zip")

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

    return 404


def send_attachment(req):
    try:
        nid = node_id_from_req_path(req)
        version_id = version_id_from_req(req)
    except ValueError:
        return 400

    node = get_node_or_version(nid, version_id, Data)

    if (node is None
            or isinstance(node, Container) and not node.has_read_access()
            or isinstance(node, Content) and not node.has_data_access()):
        return 404

    attachment_file = node.files.filter_by(filetype=u"attachment").first()
    if attachment_file is not None:
        # filename is attachment.zip
        sendZipFile(req, file.abspath)


def send_attfile(req):
    """send single attachment file to user"""
    parts = req.path[9:].split('/')

    if len(parts) < 2:
        return 400

    nid = userinput.string_to_int(parts[0])
    if nid is None:
        return 400

    version_id = version_id_from_req(req)

    node = get_node_or_version(nid, version_id, Data)

    # XXX: why do we want to send attachments from containers?
    if (node is None
            or isinstance(node, Container) and not node.has_read_access()
            or isinstance(node, Content) and not node.has_data_access()):
        return 404

    paths = ["/".join(parts[1:]), "/".join(parts[1:-1])]
    fileobjs = [fo for fo in node.files if fo.path in paths]

    if not fileobjs:
        return 404

    fileobj = fileobjs[0]

    if (fileobj.size > 16 * 1048576):
        req.reply_headers["Content-Disposition"] = u'attachment; filename="{}"'.format(fileobj.base_name).encode('utf8')

    return req.sendFile(fileobj.abspath, fileobj.mimetype)


def fetch_archived(req):
    try:
        nid = node_id_from_req_path(req)
    except ValueError:
        return 400

    node = q(Content).get(nid)

    archive = get_archive_for_node(node)
    if archive:
        try:
            archive.fetch_file_from_archive(node)
        except:
            logg.exception("exception in fetch_file_from_archive for archive %s", archive.archive_type)
            msg = "fetch archive for node failed"
            req.setStatus(500)
            req.write(msg)
        else:
            req.write('done')
    else:
        msg = "archive for node not found"
        req.setStatus(404)
        req.write(msg)
        logg.warn(msg)

    db.session.commit()


def send_from_webroot(req):
    filename = config.basedir + "/web/root" + req.path
    if os.path.isfile(filename):
        return req.sendFile(filename, getMimeType(filename)[0])
    else:
        return 404

### redirects for legacy handlers

def redirect_images(req):
    req.reply_headers["Location"] = "/image" + req.uri[7:]
    return 301