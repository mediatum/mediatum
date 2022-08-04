# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal as _tal

import core as _core
from .workflow import WorkflowStep, registerStep


def register():
    registerStep("workflowstep_deletefile")


class WorkflowStep_DeleteFile(WorkflowStep):

    default_settings = dict(
        filetype=(),
    )

    def runAction(self, node, op=""):
        if not self.settings['filetype']:  # delete all files
            for f in node.files:
                node.files.remove(f)

        else:
            for f in node.files:
                if f.filetype in self.settings['filetype']:
                    node.files.remove(f)
        self.forward(node, True)
        _core.db.session.commit()

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/deletefile.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        data["filetype"] = filter(None, (s.strip() for s in data["filetype"].split("\r\n")))
        assert tuple(data) == ("filetype",)
        self.settings = data
        _core.db.session.commit()
