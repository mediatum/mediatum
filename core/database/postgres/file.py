# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import os
from warnings import warn

from core.database.postgres import DeclarativeBase, C, FK, rel, bref, integer_pk
from core.database.postgres.node import Node
from sqlalchemy import Integer, Unicode, String, event, Table
from core.database.postgres.alchemyext import AppenderQueryWithLen
from core.file import FileMixin
from core import config


logg = logging.getLogger(__name__)


class NodeToFile(DeclarativeBase):
    __tablename__ = "node_to_file"
    __versioned__ = {}
    
    nid = C(Integer, FK(Node.id, ondelete="CASCADE"), primary_key=True)
    file_id = C(Integer, FK("file.id"), primary_key=True)


class File(DeclarativeBase, FileMixin):

    """Represents an item on the filesystem
    """
    __versioned__ = {
        "base_classes": (FileMixin, DeclarativeBase)
    }

    #: True means: physical file should be deleted when database object is deleted
    unlink_after_deletion = False


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

    __tablename__ = "file"
    id = integer_pk()
    path = C(Unicode(4096))
    filetype = C(Unicode(126))
    mimetype = C(String(255))

    nodes = rel(Node, secondary=NodeToFile.__table__, 
                backref=bref("files", lazy="dynamic", query_class=AppenderQueryWithLen), lazy="dynamic")
    
    _node_objects = rel(Node, secondary=NodeToFile.__table__, backref=bref("file_objects", viewonly=True), viewonly=True)

    def unlink(self):
        if self.exists:
            os.unlink(self.abspath)
        else:
            logg.warn("tried to unlink missing physical file %s at %s, ignored", self.id, self.path)

    def __repr__(self):
        return "File #{} ({}:{}|{}) at {}".format(
            self.id, self.path, self.filetype, self.mimetype, hex(id(self)))

    def __unicode__(self):
        return u"# {} {} {} in {}".format(self.id, self.filetype, self.mimetype, self.path)

@event.listens_for(File, 'after_delete')
def unlink_physical_file_on_delete(mapper, connection, target):
    # XXX: convert this to a SQLAlchemy 1.1 session event
    if target.unlink_after_deletion:
        if os.path.exists(target.abspath):
                target.unlink()
        else:
            logg.info("trying to unlink physical file for file with type %s for node %s, but it doesn't exist, ignoring.",
                      target.filetype, target.nid)
