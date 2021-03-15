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

import mediatumtal.tal as _tal

from .workflow import WorkflowStep, registerStep
from core.translation import t, addLabels
from schema.schema import Metafield


def register():
    #tree.registerNodeClass("workflowstep-textpage", WorkflowStep_TextPage)
    registerStep("workflowstep_textpage")
    addLabels(WorkflowStep_TextPage.getLabels())


class WorkflowStep_TextPage(WorkflowStep):

    """
        workflowstep that shows a textpage.
        attention:
            if labels are given to true or false operation user has to
            click buttons to get to next workflow step
            otherwise forward will be performed automatically by system
    """

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
        return _tal.processTAL({"text": self.get("text"), "buttons": buttons, "csrf": req.csrf_token.current_token,}, file="workflow/textpage.html", macro="textpage_show_node", request=req)

    def metaFields(self, lang=None):
        field = Metafield("text")
        field.set("label", t(lang, "admin_wfstep_textpage_text_to_display"))
        field.set("type", "htmlmemo")
        return [field]

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-textpage", "Textseite anzeigen"),
                    ("admin_wfstep_textpage_text_to_display", "Seiteninhalt"),
                ],
                "en":
                [
                    ("workflowstep-textpage", "show textpage"),
                    ("admin_wfstep_textpage_text_to_display", "Page content"),
                ]
                }
