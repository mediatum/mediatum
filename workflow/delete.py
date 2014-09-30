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
from .workflow import WorkflowStep, registerStep
import core.tree as tree


def register():
    tree.registerNodeClass("workflowstep-delete", WorkflowStep_Delete)
    registerStep("workflowstep-delete")


class WorkflowStep_Delete(WorkflowStep):

    def runAction(self, node, op=""):
        for p in node.getParents():
            try:
                p.removeChild(node)
            except tree.NoSuchNodeError:
                pass
