# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import os.path
from warnings import warn

from core import config
from utils.utils import get_filesize, get_hash


class FileMixin(object):

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
    def size(self):
        return get_filesize(self.path)

    @property
    def hash(self):
        return get_hash(self.path)

    def open(self, *args, **kwargs):
        """Opens and returns the referenced file from the file system
        :raises: IOError
        """
        return open(self.abspath, *args, **kwargs)

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