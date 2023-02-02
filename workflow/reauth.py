# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from .workflow import WorkflowStep, registerStep
from core import db


def register():
    registerStep("workflowstep_reauth")


class WorkflowStep_Reauth(WorkflowStep):

    def runAction(self, node, op=""):
        node.set("key", node.get("system.key"))
        db.session.commit()
        self.forward(node, True)
