# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflow step enables user to assign node.type and node.schema.
Type is stored in node.attrs[workflowstep.attrs["type-attribute"]]
and schema in node.attrs[workflowstep.attrs["schema-attribute"]].
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import collections as _collections

import mediatumtal.tal as _tal

import core as _core
import workflow as _workflow


def register():
    _workflow.registerStep("workflowstep_setmetadatatype")


class WorkflowStep_SetMetadatatype(_workflow.WorkflowStep):

    default_settings = {"type-attribute":None, "schema-attribute":None, "clear-files":True}

    def runAction(self, node, op=""):
        if self.settings["type-attribute"] is not None:
            node.type = node.attrs[self.settings["type-attribute"]]
        if self.settings["schema-attribute"] is not None:
            node.schema = node.attrs[self.settings["schema-attribute"]]
        if self.settings["clear-files"]:
            _collections.deque(map(node.files.remove, node.files), maxlen=0)
        _core.db.session.commit()
        self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            dict(
                type_attribute=self.settings["type-attribute"],
                schema_attribute=self.settings["schema-attribute"],
                keep_files=not self.settings["clear-files"],
                ),
            file="workflow/setmetadatatype.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        data["type-attribute"] = data["type-attribute"] or None
        data["schema-attribute"] = data["schema-attribute"] or None
        data["clear-files"] = not data.pop("keep-files",None)
        assert frozenset(data) == frozenset(self.default_settings)
        self.settings = data
        _core.db.session.commit()
