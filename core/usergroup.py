# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

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
