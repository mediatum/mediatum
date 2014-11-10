# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import os.path
from warnings import warn

from core.database.postgres import BaseFile, bref, rel
from core import config
from core.node import Node
from utils.utils import get_filesize


DATADIR = config.settings["paths.datadir"]


class File(BaseFile):

    node = rel(Node, backref=bref("files", lazy="dynamic", cascade="all, delete-orphan"))

    def __init__(self, path, filetype, mimetype, node=None, **kwargs):
        # legacy stuff
        if path.startswith(DATADIR):
            warn("file path starts with paths.datadir, should be relative", DeprecationWarning)
            path = path[len(DATADIR):]
        if "type" in kwargs:
            raise Exception("type keyword arg is not allowed anymore, use filetype")
        if "filename" in kwargs:
            raise Exception("name positional arg is not allowed anymore, use path")

        self.path = path
        self.filetype = filetype
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
    def abspath(self):
        return os.path.join(DATADIR, self.path)

    @property
    def type(self):
        warn("use File.filetype instead", DeprecationWarning)
        return self.filetype

    @property
    def size(self):
        return get_filesize(self.path)

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
