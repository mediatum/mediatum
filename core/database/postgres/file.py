# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import os
import logging
from warnings import warn
from datetime import datetime

from sqlalchemy import Table
from sqlalchemy import event
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import DateTime
from sqlalchemy import BigInteger
import humanize

from core import db, config
from core.file import FileMixin, FileVersionMixin
from core.database.postgres.node import Node
from core.database.postgres.alchemyext import AppenderQueryWithLen
from core.database.postgres import DeclarativeBase, C, FK, rel, bref, integer_pk
from utils.utils import get_filesize, sha512_from_file


logg = logging.getLogger(__name__)


class NodeToFile(DeclarativeBase):
    __tablename__ = "node_to_file"

    nid = C(Integer, FK(Node.id, ondelete="CASCADE"), primary_key=True)
    file_id = C(Integer, FK("file.id"), primary_key=True)


class File(DeclarativeBase, FileMixin):
    """Represents an item on the filesystem
    """
    __versioned__ = {
        "base_classes": (FileVersionMixin, DeclarativeBase)
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
    _size = C('size', BigInteger)
    # Checksum/hash columns
    sha512 = C(String(128))  # LargeBinary could be an alternative
    sha512_created_at = C(DateTime())
    sha512_checked_at = C(DateTime())
    sha512_ok = C(Boolean())

    nodes = rel(Node, secondary=NodeToFile.__table__, 
                backref=bref("files", lazy="dynamic", query_class=AppenderQueryWithLen), lazy="dynamic")
    
    _node_objects = rel(Node, secondary=NodeToFile.__table__, backref=bref("file_objects", viewonly=True), viewonly=True)

    def unlink(self):
        if self.exists:
            os.unlink(self.abspath)
        else:
            logg.warning("tried to unlink missing physical file %s at %s, ignored", self.id, self.path)

    def __repr__(self):
        return "File #{} ({}:{}|{}) at {}".format(
            self.id, self.path, self.filetype, self.mimetype, hex(id(self)))

    def __unicode__(self):
        return u"# {} {} {} in {}".format(self.id, self.filetype, self.mimetype, self.path)

    @property
    def size(self):
        """Return size of file in bytes"""
        if self._size is None:
            return get_filesize(self.path)
        return self._size

    @property
    def size_humanized(self):
        """Return string with the size in human-friendly format, e.g. '7.9 kB'"""
        return humanize.naturalsize(self.size)

    def calculate_sha512(self):
        """Calculate the hash from the file on disk."""
        if not self.exists:
            return None
        return sha512_from_file(self.abspath)

    def update_sha512(self):
        """Overwrite the stored checksum value with the current checksum of the file on disk.
        Use with caution, should not be necessary under usual circumstances!"""
        if not self.exists:
            return None
        logg.info('Updating sha512 for file ID: %s.', self.id)
        self.sha512 = self.calculate_sha512()
        self.sha512_ok = True
        self.sha512_created_at = self.sha512_checked_at = datetime.utcnow()
        self._size = get_filesize(self.path)
        return self.sha512

    def get_or_create_sha512(self):
        """Return the stored hash. If there is none, create and store it."""
        if not self.exists:
            return None, False
        created = False
        if not self.sha512:
            created = True
            logg.info('Checksum not in DB, creating it for file ID: %s.', self.id)
            self.update_sha512()
        return self.sha512, created

    def verify_checksum(self):
        """Make sure the file exists and has the same checksum as before"""
        if not self.exists:
            #raise IOError()
            logg.warning('check_checksum: file %s does not exist at %s!', self.id, self.abspath)
            self.sha512_ok = None
            return None
        self.sha512_checked_at = datetime.utcnow()
        sha_stored, created = self.get_or_create_sha512()
        if created:
            # checksum was just created, skip a second calculation of the hash
            return True
        else:
            sha_calculated = self.calculate_sha512()
            if sha_stored == sha_calculated and sha_calculated is not None:
                logg.debug('Matching checksums :) for file ID: %s.', self.id)
                self.sha512_ok = True
            else:
                logg.warning('Checksum mismatch for file ID: %s.', self.id)
                self.sha512_ok = False
        return self.sha512_ok


@event.listens_for(File, 'after_delete')
def unlink_physical_file_on_delete(mapper, connection, target):
    # XXX: convert this to a SQLAlchemy 1.1 session event
    if target.unlink_after_deletion:
        if os.path.exists(target.abspath):
                target.unlink()
        else:
            logg.info("trying to unlink physical file for file with type %s for node %s, but it doesn't exist, ignoring.",
                      target.filetype, target.nid)
