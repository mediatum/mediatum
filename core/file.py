# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function
import os.path
from warnings import warn

from core.database.postgres import BaseFile
from core import config
from utils.utils import get_filesize


class File(BaseFile):

    def __init__(self, path, filetype, mimetype, node=None, **kwargs):
        # legacy stuff
        if path.startswith(config.settings["paths.datadir"]):
            warn("file path starts with paths.datadir, should be relative", DeprecationWarning)
            path = path[len(config.settings["paths.datadir"]):]
        if "type" in kwargs:
            warn("type positional arg is deprecated, use filetype", DeprecationWarning)
        if "filename" in kwargs:
            warn("name positional arg is deprecated, use path", DeprecationWarning)

        self.path = path
        self.type = filetype
        self.mimetype = mimetype
        if node is not None:
            self.node = node

    def _ni(self):
        raise NotImplementedError()

    clone = _add = _delete = _ni

    @property
    def base_name(self):
        return os.path.basename(self.path)

    @property
    def size(self):
        return get_filesize(self.path)

    def open(self):
        """Opens and returns the referenced file from the file system
        :raises: IOError
        """
        return open(self.path)

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
        warn("use File.open() instead, see doc", DeprecationWarning)
        self.open()

    def getSize(self):
        warn("use File.size instead", DeprecationWarning)
        return self.size

