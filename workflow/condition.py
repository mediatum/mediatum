"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Peter Heckl <heckl@ub.tum.de>

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

from .workflow import WorkflowStep, registerStep, getNodeWorkflow
from core.translation import t, addLabels
from core import db
from schema.schema import Metafield

q = db.query

def register():
    #tree.registerNodeClass("workflowstep-condition", WorkflowStep_Condition)
    registerStep("workflowstep_condition")
    addLabels(WorkflowStep_Condition.getLabels())


class WorkflowStep_Condition(WorkflowStep):

    def runAction(self, node, op=""):
        condition = self.get("condition")
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
        newstep.children.append(node)
        db.session.commit()
        self.children.remove(node)
        db.session.commit()

        newstep.runAction(node, True)  # always run true operation

    def metaFields(self, lang=None):
        field = Metafield("condition")
        field.set("label", t(lang, "admin_wfstep_condition"))
        field.set("type", "text")
        return [field]

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-condition", "Bedingungsfeld"),
                    ("admin_wfstep_condition", "Bedingung"),
                ],
                "en":
                [
                    ("workflowstep-condition", "Condition field"),
                    ("admin_wfstep_condition", "Condition"),

                ]
                }
