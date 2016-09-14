"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2009 Matthias Kramm <kramm@in.tum.de>

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

    logg.warn("archive manager {} for node {} not loaded".format(archive_type, node.id))
