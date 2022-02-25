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
import codecs
import functools as _functools
import logging
import os
import re as _re
import shutil
import time
import utils as _utils_utils
from core import db, File, config
from .utils import getMimeType
from core.config import resolve_datadir_path

logg = logging.getLogger(__name__)
q = db.query


sanitize_filename = _functools.partial(_re.compile("[^a-zA-Z0-9._-]").sub, "")


def getImportDir():
    incoming_dir = resolve_datadir_path("incoming")
    uploaddir = os.path.join(incoming_dir, time.strftime("%Y-%b"))

    if not os.path.exists(uploaddir):
        os.mkdir(uploaddir)

    return uploaddir


def importFile(destname, sourcefileobj, filetype=None):
    """
    copies an imported file to the incoming directory and returns a File-object (entry in file-table)
    for it.
    The name for the imported file is specified by the destname (only filename without path),
    which gets a secure_token prefix and the path of the incoming directory
    :param destname: name of the uploaded file (without path)
    :param sourcefileobj: sourcefiledescriptor, e.g. werkzeug.Filestorage, used for copy
    :param filetype: if specified overrides filetype
    :return: File-object of the imported file.
    """
    assert destname > ""
    destname = (_utils_utils.gen_secure_token(128), os.path.basename(destname))
    destname = os.path.join(getImportDir(), ".".join(destname))

    with open(destname,"wb") as destfile:
        shutil.copyfileobj(sourcefileobj, destfile)

    mimetype, filetype_ = getMimeType(destname.lower())

    return File(destname, filetype or filetype_, mimetype)


def importFileIntoDir(destdir, tempname):
    filename = os.path.basename(tempname)

    dest_dirpath = os.path.join(getImportDir(), destdir)
    dest_filepath = os.path.join(dest_dirpath, filename)

    if not os.path.exists(dest_dirpath):
        os.mkdir(dest_dirpath)

    shutil.copyfile(tempname, dest_filepath)

    r = tempname.lower()
    mimetype, filetype = getMimeType(r)

    return File(os.path.join(dest_filepath), filetype, mimetype)


def importFileRandom(tempname):
    filename = os.path.basename(tempname)
    uploaddir = getImportDir()

    destfile = _utils_utils.gen_secure_token(128) + os.path.splitext(filename)[1]
    destname = os.path.join(uploaddir, destfile)
    shutil.copyfile(tempname, destname)

    r = tempname.lower()
    mimetype, filetype = getMimeType(r)
    return File(destname, filetype, mimetype)
