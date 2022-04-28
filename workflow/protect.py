# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from .workflow import WorkflowStep, registerStep
from utils.utils import mkKey
from core import db


def register():
    #tree.registerNodeClass("workflowstep-protect", WorkflowStep_Protect)
    registerStep("workflowstep_protect")


class WorkflowStep_Protect(WorkflowStep):

    def runAction(self, node, op=""):
        node.set("key", mkKey())
        db.session.commit()
        self.forward(node, True)
