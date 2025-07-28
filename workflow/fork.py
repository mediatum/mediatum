# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflowstep forwards automatically.
Admin chooses an attribute which determines True-/False-forwarding.
node.attrs[workflowstep.attrs["attribute"]] empty string forwards to False-path.
node.attrs[workflowstep.attrs["attribute"]] non-empty to True-path.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

from mediatumtal import tal as _tal

import core as _core
import core.translation as _core_translation
import workflow as _workflow


def register():
    _workflow.registerStep("workflowstep_fork")


class WorkflowStep_Fork(_workflow.WorkflowStep):

    default_settings = dict(attribute="")

    def runAction(self, node, op=""):
        if not self.settings["attribute"]:
            raise RuntimeError(_core_translation.translate_in_request("admin_mandatory_info"))
        self.forward(node, bool(node.attrs.get(self.settings["attribute"])))

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            dict(attribute=self.settings["attribute"]),
            file="workflow/fork.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert frozenset(data) == frozenset(self.default_settings)
        if not data["attribute"]:
            raise RuntimeError(_core_translation.translate_in_request("admin_mandatory_info"))
        self.settings = data
        _core.db.session.commit()
