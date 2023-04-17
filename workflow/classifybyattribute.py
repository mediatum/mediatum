# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Institute is stored in this workflowstep.attrs["target-attribute-name"] as key.
Processing node will be appended to nodes where their identifies are found in
processing node.attrs[self.attrs["target-attribute-name"]].
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import core as _core
import schema.schema as _schema_schema
import workflow as _workflow


def register():
    _workflow.registerStep("workflowstep_classifybyattribute")
    _core.translation.addLabels(WorkflowStep_ClassifyByAttribute.getLabels())


class WorkflowStep_ClassifyByAttribute(_workflow.WorkflowStep):

    def runAction(self, node, op=""):
        parents = node.attrs[self.attrs["target-attribute-name"]].split()
        for nid in frozenset(map(int, parents)):
            _core.db.query(_core.Node).get(nid).children.append(node)

        self.forward(node, True)

    def metaFields(self, lang=None):
        field = _schema_schema.Metafield("target-attribute-name")
        label = "classifybyattribute-target-attribute-name"
        field.set(
            "label",
            _core.translation.translate(lang, label) if lang else _core.translation.translate_in_request(label),
        )
        field.set("type", "text")
        return [field]

    @staticmethod
    def getLabels():
        return dict(
            de=[
                    ("workflowstep_classifybyattribute", "Klassifizieren nach Attribute"),
                    ("classifybyattribute-target-attribute-name", "Metadatenfeld-Name für Knoten-IDs"),
                ],
            en=[
                    ("workflowstep_classifybyattribute", "Classify by Attribute"),
                    ("classifybyattribute-target-attribute-name", "Metafield Name for Node IDs"),
                ],
        )
