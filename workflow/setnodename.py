# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
the step sets the node name from a selectable attribute
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

from mediatumtal import tal as _tal

import core as _core
import workflow as _workflow


def register():
    _workflow.registerStep("workflowstep_setnodename")


class WorkflowStep_SetNodeName(_workflow.WorkflowStep):

    default_settings = dict(sourceattributename="")

    def runAction(self, node, op=""):
        node.name = node.attrs[self.settings["sourceattributename"]]
        _core.db.session.commit()
        self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
                self.settings,
                file="workflow/setnodename.html",
                macro="workflow_step_type_config",
                request=req,
            )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert tuple(data) == ("sourceattributename",)
        self.settings = data
        _core.db.session.commit()
