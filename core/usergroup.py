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
from __future__ import division
from __future__ import print_function

from warnings import warn


class UserGroupMixin(object):

    def getDescription(self):
        warn("use UserGroup.description", DeprecationWarning)
        return self.description

    def setDescription(self, d):
        warn("use UserGroup.description", DeprecationWarning)
        self.description = d

    def getOption(self):
        raise Exception("obsolete, use UserGroup.is_editor_group, UserGroup.is_admin or UserGroup.is_workflow_editor_group")

    def setOption(self, o):
        raise Exception("obsolete, use UserGroup.is_editor_group, UserGroup.is_admin or UserGroup.is_workflow_editor_group")

    def getSchemas(self):
        """Returns metadatatypes which can be read by members of this group"""
        raise Exception("obsolete")

    def getHideEdit(self):
        raise Exception("use UserGroup.hidden_edit_functions")

    def setHideEdit(self, value):
        raise Exception("use UserGroup.hidden_edit_functions")
