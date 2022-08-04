# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import core as _core
from .workflow import WorkflowStep, registerStep
from utils.utils import mkKey


def register():
    registerStep("workflowstep_protect")


class WorkflowStep_Protect(WorkflowStep):

    def runAction(self, node, op=""):
        node.set("key", mkKey())
        _core.db.session.commit()
        self.forward(node, True)
