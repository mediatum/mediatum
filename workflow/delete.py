# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

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
