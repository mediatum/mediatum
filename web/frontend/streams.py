"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

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
import glob
import random
import zipfile
import time

from core import db
from core import Node
import core.config as config
import core.athana as athana
from core.archive import archivemanager
import utils.utils
from utils.utils import get_filesize, join_paths, clean_path, getMimeType
from sqlalchemy.orm.exc import NoResultFound
from core import Node
from schema.schema import existMetaField
from contenttypes import Container, Directory


logg = logging.getLogger(__name__)
q = db.query

IMGNAME = re.compile("/?(attachment|doc|images|thumbs|thumb2|file|download|archive)/([^/]*)(/(.*))?$")


def incUsage(node):
    # no statistics logging here at the moment, uneeded
    pass


def splitpath(path):
    m = IMGNAME.match(path)
    if m is None:
        return path
    try:
        return m.group(2), m.group(4)
    except:
        return m.group(2), None


def send_image(req):
    n = q(Node).get(splitpath(req.path)[0])

    if not isinstance(n, Node):
        return 404

    for f in n.files:
        if f.filetype == "image":
            return req.sendFile(f.abspath, f.mimetype)
    return 404


def send_image_watermark(req):
    result = splitpath(req.path)
    n = q(Node).get(result[0])

    if not isinstance(n, Node):
        return 404

    for f in n.files:
        if f.filetype == "original_wm":
            return req.sendFile(f.abspath, getMimeType(f.abspath))

    return 404


def send_rawimage(req):
    n = q(Node).get(splitpath(req.path)[0])

    if not isinstance(n, Node):
        return 404
    if not isinstance(n, Directory) and not n.has_data_access():
        return 403
    for f in n.files:
        if f.filetype == "original":
            incUsage(n)
            return req.sendFile(f.abspath, f.mimetype)
    return 404


def send_rawfile(req, n=None):
    if not n:
        id, filename = splitpath(req.path)
        n = q(Node).get(id)
        if not isinstance(n, Node):
            return 404

    if not isinstance(n, Container) and not n.has_data_access():
        return 403
    for f in n.files:
        if f.filetype == "original":
            incUsage(n)
            return req.sendFile(f.abspath, f.mimetype)
    return 404


def send_thumbnail(req):
    n = q(Node).get(splitpath(req.path)[0])
    if not isinstance(n, Node):
        return 404
    for f in n.files:
        if f.type == "thumb":
            if os.path.isfile(f.abspath):
                return req.sendFile(f.abspath, f.mimetype)

    for p in athana.getFileStorePaths("/img/"):
        for test in ["default_thumb_%s_%s.*" % (n.type, n.schema),
                     "default_thumb_%s.*" % n.schema,
                     "default_thumb_%s.*" % n.type]:
            fps = glob.glob(os.path.join(config.basedir, p[2:], test))
            if fps:
                thumb_mimetype, thumb_type = utils.utils.getMimeType(fps[0])
                return req.sendFile(fps[0], thumb_mimetype, force=1)
    return req.sendFile(config.basedir + "/web/img/questionmark.png", "image/png", force=1)


def send_thumbnail2(req):
    n = q(Node).get(splitpath(req.path)[0])
    if not isinstance(n, Node):
        return 404
    for f in n.files:
        if f.type.startswith("presentat"):
            if os.path.isfile(f.abspath):
                return req.sendFile(f.abspath, f.mimetype)
    # fallback
    for f in n.files:
        if f.type == "image":
            if os.path.isfile(f.abspath):
                return req.sendFile(f.abspath, f.mimetype)

    # fallback2
    for p in athana.getFileStorePaths("/img/"):
        for test in [
                "default_thumb_%s_%s.*" % (n.type, n.schema),
                "default_thumb_%s.*" % n.schema,
                "default_thumb_%s.*" % n.type]:
            # fps = glob.glob(os.path.join(config.basedir, theme.getImagePath(), "img", test))
            fps = glob.glob(os.path.join(config.basedir, p[2:], test))
            if fps:
                thumb_mimetype, thumb_type = utils.utils.getMimeType(fps[0])
                return req.sendFile(fps[0], thumb_mimetype, force=1)
    return 404


def send_doc(req):
    n = q(Node).get(splitpath(req.path)[0])
    if not isinstance(n, Node):
        return 404
    if not isinstance(n, Directory) and not n.has_data_access():
        return 403
    for f in n.files:
        if f.type in ["doc", "document"]:
            incUsage(n)
            return req.sendFile(f.abspath, f.mimetype)
    return 404


def send_file(req, download=0):
    id, filename = splitpath(req.path)
    if id.endswith("_transfer.zip"):
        id = id[:-13]

    n = q(Node).get(id)
    if not isinstance(n, Node):
        return 404
    if not isinstance(n, Container) and not n.has_data_access():
        return 403
    file = None

    if filename is None and n:
        # build zip-file and return it
        zipfilepath, files_written = build_transferzip(n)
        if files_written == 0:
            return 404
        send_result = req.sendFile(zipfilepath, "application/zip")
        if os.sep == '/':  # Unix?
            os.unlink(zipfilepath)  # unlinking files while still reading them only works on Unix/Linux
        return send_result

    # try full filename
    for f in n.files:
        if f.base_name == filename:
            incUsage(n)
            file = f
            break

    # try only extension
    if not file and n.get("archive_type") == "":
        file_ext = os.path.splitext(filename)[1]
        for f in n.files:
            if os.path.splitext(f.getName())[1] == file_ext and f.filetype in ['doc', 'document', 'original', 'mp3']:
                incUsage(n)
                file = f
                break

    # XXX: temporary fix for getSchema(), hasattr can be removed later when all data nodes have a schema
    if hasattr(n, "schema") and existMetaField(n.schema, 'nodename'):
        display_file_name = '{}.{}'.format(os.path.splitext(os.path.basename(n.name))[0], os.path.splitext(filename)[-1].strip('.'))
    else:
        display_file_name = filename

    # try file from archivemanager
    if not file and n.get("archive_type") != "":
        am = archivemanager.getManager(n.get("archive_type"))
        req.reply_headers["Content-Disposition"] = u'attachment; filename="{}"'.format(display_file_name).encode('utf8')
        return req.sendFile(am.getArchivedFileStream(n.get("archive_path")), "application/x-download")

    if not file:
        return 404

    req.reply_headers["Content-Disposition"] = u'attachment; filename="{}"'.format(display_file_name).encode('utf8')
    return req.sendFile(file.abspath, f.mimetype)


def send_file_as_download(req):
    return send_file(req, download=1)


def send_attachment(req):
    nid, filename = splitpath(req.path)
    node = q(Node).get(nid)
    if not isinstance(node, Node):
        return 404
    if not isinstance(Directory) and not node.has_data_access():
        return 403
    # filename is attachment.zip
    for file in node.files:
        if file.type == "attachment":
            sendZipFile(req, file.abspath)
            break


def sendBibFile(req, path):
    req.reply_headers['Content-Disposition'] = "attachment; filename=export.bib"
    req.sendFile(path, getMimeType(path))
    if os.sep == '/':  # Unix?
        os.unlink(path)  # unlinking files while still reading them only works on Unix/Linux


def sendZipFile(req, path):
    tempfile = join_paths(config.get("paths.tempdir"), unicode(random.random())) + ".zip"
    zip = zipfile.ZipFile(tempfile, "w")
    zip.debug = 3

    def r(p):
        if os.path.isdir(join_paths(path, p)):
            for file in os.listdir(join_paths(path, p)):
                r(join_paths(p, file))
        else:
            while len(p) > 0 and p[0] == "/":
                p = p[1:]
            try:
                zip.write(join_paths(path, p), p)
            except:
                pass

    r("/")
    zip.close()
    req.reply_headers['Content-Disposition'] = "attachment; filename=shoppingbag.zip"
    req.sendFile(tempfile, "application/zip")
    if os.sep == '/':  # Unix?
        os.unlink(tempfile)  # unlinking files while still reading them only works on Unix/Linux


#
# send single attachment file to user
#
def send_attfile(req):
    f = req.path[9:].split('/')
    node = q(Node).get(f[0])
    if not isinstance(node, Node):
        return 404
    if not isinstance(Directory) and not node.has_data_access():
        return 403
    if len([file for file in node.files if file.abspath in ["/".join(f[1:]), "/".join(f[1:-1])]]) == 0:  # check filepath
        return 403

    filename = clean_path("/".join(f[1:]))
    path = join_paths(config.get("paths.datadir"), filename)
    mime, type = getMimeType(filename)
    if (get_filesize(filename) > 16 * 1048576):
        req.reply_headers["Content-Disposition"] = u'attachment; filename="{}"'.format(filename).encode('utf8')

    return req.sendFile(path, mime)


def get_archived(req):
    logg.debug("send archived")
    id, filename = splitpath(req.path)
    node = q(Node).get(id)
    node.set("archive_state", "1")
    if not archivemanager:
        msg = "-no archive module loaded-"
        req.write(msg)
        logg.warn(msg)
        return

    archiveclass = ""
    for item in config.get("archive.class").split(";"):
        if item.endswith(node.get("archive_type")):
            archiveclass = item + ".py"
            break

    if archiveclass:  # start process from archive
        os.chdir(config.basedir)
        os.system("python %s %s" % (archiveclass, node.id))

    st = ""
    while True:  # test if process is still running
        attrs = tree.db.getAttributes(id)
        if "archive_state" in attrs.keys():
            st = attrs['archive_state']
        time.sleep(1)
        if st == "2":
            break

    for n in node.getAllChildren():
        tree.remove_from_nodecaches(n)
    req.write('done')


def get_root(req):
    filename = config.basedir + "/web/root" + req.path
    if os.path.isfile(filename):
        return req.sendFile(filename, getMimeType(filename)[0])
    else:
        return 404


def get_all_file_paths(basedir):
    res = []
    for dirpath, dirnames, filenames in os.walk(basedir):
        for fn in filenames:
            res.append(os.path.join(dirpath, fn))
    return res


def build_transferzip(node):
    nid = node.id
    zipfilepath = join_paths(config.get("paths.tempdir"), nid + "_transfer.zip")
    if os.path.exists(zipfilepath):
        zipfilepath = join_paths(config.get("paths.tempdir"), nid + "_" + unicode(random.random()) + "_transfer.zip")

    zip = zipfile.ZipFile(zipfilepath, "w", zipfile.ZIP_DEFLATED)
    files_written = 0

    for n in node.getAllChildren():
        if n.isActiveVersion():
            for fn in n.files:
                if fn.filetype in ['doc', 'document', 'zip', 'attachment', 'other']:
                    fullpath = fn.abspath
                    if os.path.isfile(fullpath) and os.path.exists(fullpath):
                        dirname, filename = os.path.split(fullpath)
                        logg.debug("adding to zip: %s as %s", fullpath, filename)
                        zip.write(fullpath, filename)
                        files_written += 1
                    if os.path.isdir(fullpath):
                        for f in get_all_file_paths(fullpath):
                            newpath = f.replace(fullpath, "")
                            logg.debug("adding from % to zip %s as %s", fullpath, f, newpath)
                            zip.write(f, newpath)
                        files_written += 1
                    if os.path.isdir(fullpath):
                        for f in get_all_file_paths(fullpath):
                            newpath = f.replace(fullpath, "")
                            print "adding from ", fullpath, "to zip: ", f, "as", newpath
                            zip.write(f, newpath)
                            files_written += 1
    zip.close()

    return zipfilepath, files_written


def build_filelist(node):
    "build file list for generation of xmetadissplus xml"
    files_written = 0
    result_list = []

    for n in node.getAllChildren():
        if n.isActiveVersion():
            for fn in n.files:
                if fn.filetype in ['doc', 'document', 'zip', 'attachment', 'other']:
                    fullpath = fn.abspath
                    if os.path.isfile(fullpath) and os.path.exists(fullpath):
                        dirname, filename = os.path.split(fullpath)
                        result_list.append([filename, fn.getSize()])
                        files_written += 1
                    if os.path.isdir(fullpath):
                        for f in get_all_file_paths(fullpath):
                            dirname, filename = os.path.split(f)
                            result_list.append([filename, utils.utils.get_filesize(f)])
                            files_written += 1
                        if os.path.isdir(fullpath):
                            for f in get_all_file_paths(fullpath):
                                dirname, filename = os.path.split(f)
                                result_list.append([filename, utils.utils.get_filesize(f)])
                                files_written += 1

    return result_list


def get_transfer_url(n):
    "get transfer url for oai format xmetadissplus"
    filecount = len(build_filelist(n))
    if filecount < 2:
        transfer_filename = n.id + ".pdf"
        transferurl = u"http://{}/doc/{}/".format(config.get("host.name"), n.id, transfer_filename)
    else:
        transfer_filename = n.id + "_transfer.zip"
        transferurl = u"http://{}/file/{}/".format(config.get("host.name"), n.id, transfer_filename)

    return transferurl
