# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflow step enables user to assign template from metafield to node. Metafield is stored in
workflowstep.attrs.["target-metadata-name"].
If processing node.attrs[workflowstep.attrs.["target-metadata-name"]].
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import core as _core
from mediatumtal import tal as _tal
import workflow as _workflow


def register():
    _workflow.registerStep("workflowstep_template2metadata")


class WorkflowStep_Template2Metadata(_workflow.WorkflowStep):

    default_settings = {'empty-remove':False, 'strip-eol': False, 'tal-template':"", 'target-metadata-name':""}

    def runAction(self, node, op=""):
        assert self.settings["tal-template"]
        assert self.settings["target-metadata-name"]

        text = _tal.getTALstr(self.settings["tal-template"], dict(node=node))
        if self.settings["strip-eol"]:
            text = text.rstrip("\n")
        if (not text) and self.settings["empty-remove"]:
            node.attrs.pop(self.settings["target-metadata-name"], None)
        else:
            node.attrs[self.settings["target-metadata-name"]] = text
        _core.db.session.commit()
        self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            dict(
                empty_remove=self.settings["empty-remove"],
                strip_eol=self.settings["strip-eol"],
                tal_template=self.settings["tal-template"],
                target_metadata_name=self.settings["target-metadata-name"],
                ),
            file="workflow/template2metadata.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert data["tal-template"]
        assert data["target-metadata-name"]
        data["empty-remove"] = bool(data.get("empty-remove"))
        data["strip-eol"] = bool(data.get("strip-eol"))
        assert frozenset(data) == frozenset(self.default_settings)
        self.settings = data
        _core.db.session.commit()
