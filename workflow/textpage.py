# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

from core import db as _db
import core.csrfform as _core_csrfform
from .workflow import WorkflowStep, registerStep


def register():
    registerStep("workflowstep_textpage")


class WorkflowStep_TextPage(WorkflowStep):

    """
        workflowstep that shows a textpage.
        attention:
            if labels are given to true or false operation user has to
            click buttons to get to next workflow step
            otherwise forward will be performed automatically by system
    """

    default_settings = dict(
        htmltext="",
    )

    def runAction(self, node, op=""):
        pass

    def show_workflow_node(self, node, req):
        if "gotrue" in req.params:
            self.forward(node, True)
            return self.forwardAndShow(node, True, req, forward=False)
        if "gofalse" in req.params:
            self.forward(node, False)
            return self.forwardAndShow(node, False, req, forward=False)

        if self.getTrueLabel(language=node.get("system.wflanguage")) == "" and self.getFalseLabel(
                language=node.get("system.wflanguage")) == "":
            buttons = []
            self.forward(node, True)
        else:
            buttons = self.tableRowButtons(node)
        return _tal.processTAL(
                dict(htmltext=self.settings["htmltext"], buttons=buttons, csrf=_core_csrfform.get_token()),
                file="workflow/textpage.html",
                macro="textpage_show_node",
                request=req,
            )

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/textpage.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        data.setdefault("htmltext", "")
        assert tuple(data) == ("htmltext",)
        self.settings = data
        _db.session.commit()
