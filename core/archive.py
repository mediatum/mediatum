# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging


logg = logging.getLogger(__name__)

archives = {}


class Archive(object):

    NOT_PRESENT = 0
    PENDING = 1
    PRESENT = 2

    archive_type = None

    def get_archive_path(self, node):
        return node.system_attrs[u"archive_path"]

    def fetch_file_from_archive(self, node):
        None

    def get_local_filepath(self, node):
        """Returns the path to the real file on disk."""
        None

    def get_state(self, node):
        pass

    def get_mimetype(self, node):
        pass


def register_archive(archive):
    """XXX: we could support more archives of the same type, see Authenticators"""
    archives[archive.archive_type] = archive

    logg.info("registered archive %s", archive.archive_type)


def get_archive_for_node(node):
    archive_type = node.system_attrs.get("archive_type")
    if not archive_type:
        return

    manager = archives.get(archive_type)
    if manager:
        return manager

    logg.warning("archive manager %s for node %s not loaded", archive_type, node.id)
