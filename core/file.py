# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division

import codecs
import logging
import os.path
from warnings import warn

from core import config
from utils.utils import get_filesize, get_hash


logg = logging.getLogger(__name__)


class FileMixin(object):

    # Filetypes which are uploaded by the user, used e.g. in calculation of checksums
    ORIGINAL_FILETYPES = [u'document', u'original', u'video', u'audio']  # 'original' for images, audio, ...]

    def _ni(self):
        raise NotImplementedError()

    clone = _add = _delete = _ni

    @property
    def base_name(self):
        return os.path.basename(self.path)

    @property
    def abspath(self):
        if os.path.isabs(self.path):
            return self.path
        else:
            return os.path.join(config.settings["paths.datadir"], self.path)

    @property
    def _path(self):
        warn("use File.path instead", DeprecationWarning)
        return self.path

    @property
    def type(self):
        warn("use File.filetype instead", DeprecationWarning)
        return self.filetype

    @property
    def hash(self):
        return get_hash(self.path)

    @property
    def exists(self):
        return os.path.isfile(self.abspath)

    def open(self, *args, **kwargs):
        """Opens and returns the referenced file from the file system
        :raises: IOError
        """
        if not "encoding" in kwargs:
            kwargs["encoding"] = "utf8"
        return codecs.open(self.abspath, *args, **kwargs)

    def unlink(self):
        if self.exists:
            os.unlink(self.abspath)
        else:
            logg.warning("tried to unlink missing physical file %s at %s, ignored", self.id, self.path)

    #  Deprecated methods
    def getType(self):
        warn("use File.type instead", DeprecationWarning)
        return self.filetype

    def getMimeType(self):
        warn("use File.mimetype instead", DeprecationWarning)
        return self.mimetype

    def getName(self):
        warn("use File.base_name instead", DeprecationWarning)
        return self.base_name

    def retrieveFile(self):
        warn("use File.open() or File.abspath instead, see doc", DeprecationWarning)
        return self.abspath

    def getSize(self):
        warn("use File.size instead", DeprecationWarning)
        return self.size


class FileVersionMixin(FileMixin):
    """Override methods from FileMixin for version objects of files
    """

    @property
    def size(self):
        """Return size of file in bytes"""
        if self._size is None:
            self._size = get_filesize(self.path)
        return self._size
