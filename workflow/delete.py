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

from .workflow import WorkflowStep, registerStep
from core import db
from utils.utils import suppress

def register():
    #tree.registerNodeClass("workflowstep-delete", WorkflowStep_Delete)
    registerStep("workflowstep_delete")


class WorkflowStep_Delete(WorkflowStep):

    def runAction(self, node, op=""):
        for p in node.parents:
            with suppress(Exception, warn=False):
                p.children.remove(node)
                db.session.commit()
