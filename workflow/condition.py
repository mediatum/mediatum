# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal as _tal

from .workflow import WorkflowStep, registerStep, getNodeWorkflow
from core import db

q = db.query

def register():
    registerStep("workflowstep_condition")


class WorkflowStep_Condition(WorkflowStep):

    default_settings = dict(
        condition="",
    )

    def runAction(self, node, op=""):
        condition = self.settings["condition"]
        gotoFalse = 1
        if condition.startswith("attr:"):
            hlp = condition[5:].split("=")
            if node.get(hlp[0]) == hlp[1]:
                gotoFalse = 0
        elif condition.startswith("schema="):
            if node.schema in condition[7:].split(";"):
                gotoFalse = 0
        elif condition.startswith("type="):
            if node.getContentType() in condition[5:].split(";"):
                gotoFalse = 0
        elif condition.startswith("hasfile:"):
            hlp = condition[8:].split(".")
            for f in node.files:
                if len(hlp) == 1:  # only file type
                    if f.filetype == hlp[0]:
                        gotoFalse = 0
                        break
                if len(hlp) == 2:  # file itself
                    if f.base_name == condition[8:]:
                        gotoFalse = 0
                        break
        elif condition == "hasfile":  # just test if there is file at all
            if len(node.files) == 0:
                gotoFalse = 0

        if gotoFalse:
            newstep = getNodeWorkflow(node).getStep(self.getFalseId())
        else:
            newstep = getNodeWorkflow(node).getStep(self.getTrueId())

        # move node to correct next step depending on condition evaluation
        self.children.remove(node)
        newstep.children.append(node)
        db.session.commit()

        newstep.runAction(node, True)  # always run true operation

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/condition.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert tuple(data) == ("condition",)
        self.settings = data
        db.session.commit()
