"""
 mediatum - a multimedia content repository

 Copyright (C) 2013 Arne Seifert <arne.seifert@tum.de>

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

import core.tree as tree
from .workflow import WorkflowStep, registerStep
from utils.utils import mkKey
from core.translation import addLabels


def register():
    tree.registerNodeClass("workflowstep-reauth", WorkflowStep_Reauth)
    registerStep("workflowstep-reauth")
    addLabels(WorkflowStep_Reauth.getLabels())


class WorkflowStep_Reauth(WorkflowStep):

    def runAction(self, node, op=""):
        node.set("key", node.get("system.key"))
        self.forward(node, True)

    @staticmethod
    def getLabels():
        return {"de": [("workflowstep-reauth", 'Re-Auth'), ],
                "en": [("workflowstep-reauth", 'Re-Auth'), ]}
