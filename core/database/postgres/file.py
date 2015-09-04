# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from warnings import warn

from core.database.postgres import DeclarativeBase, C, FK, rel, bref
from core.database.postgres.node import Node
from sqlalchemy import Integer, Unicode, String
from core.database.postgres.alchemyext import AppenderQueryWithLen
from core.file import FileMixin
from core import config


class File(DeclarativeBase, FileMixin):

    """Represents an item on the filesystem
    """
    __versioned__ = {
        "base_classes": (FileMixin, DeclarativeBase)
    }

    def __init__(self, path, filetype, mimetype, node=None, **kwargs):
        # legacy stuff
        datadir = config.settings["paths.datadir"]
        if path.startswith(datadir):
            warn("file path starts with paths.datadir, should be relative", DeprecationWarning)
            path = path[len(datadir):]
        if "type" in kwargs:
            raise Exception("type keyword arg is not allowed anymore, use filetype")
        if "filename" in kwargs:
            raise Exception("name positional arg is not allowed anymore, use path")

        self.path = path
        self.filetype = filetype
        self.mimetype = mimetype
        if node is not None:
            self.node = node

    __tablename__ = "nodefile"
    nid = C(Integer, FK(Node.id, ondelete="CASCADE"), primary_key=True, index=True)
    path = C(Unicode(4096), primary_key=True)
    filetype = C(Unicode(126), primary_key=True)
    mimetype = C(String(126))

    node = rel(Node, backref=bref("files", lazy="dynamic", cascade="all, delete-orphan", query_class=AppenderQueryWithLen))

    def __repr__(self):
        return "File for Node #{} ({}:{}|{}) at {}".format(
            self.nid, self.path, self.filetype, self.mimetype, hex(id(self)))
