# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
(key-value) pairs as metadata are stored in file attached to this workflowstep.
Processing node attrs will be set or removed according to these (key-value) pairs,
removed in case value is None.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import os as _os

import ruamel.yaml as _ruamel_yaml

import core as _core
import schema.schema as _schema_schema
import workflow as _workflow


_yaml_loader = _ruamel_yaml.YAML(typ="safe", pure=True).load


def register():
    _workflow.registerStep("workflowstep_updateattributesfixed")
    _core.translation.addLabels(WorkflowStep_UpdateAttributesFixed.getLabels())


class WorkflowStep_UpdateAttributesFixed(_workflow.WorkflowStep):

    def runAction(self, node, op=""):
        with open(_os.path.join(_core.config.get("paths.datadir"), self.files[0].path), "rb") as f:
            data = _yaml_loader(f)
        node.attrs.update(data)
        for k, v in data.iteritems():
            if v is None:
                del node.attrs[k]

        if hasattr(node, "event_metadata_changed"):
            node.event_metadata_changed()

        _core.db.session.commit()

        self.forward(node, True)

    def metaFields(self, lang=None):
        field = _schema_schema.Metafield("upload_fileatt")
        label = "updateattributesfixed-upload-fileatt"
        field.set(
            "label",
            _core.translation.translate(lang, label) if lang else _core.translation.translate_in_request(label),
        )
        field.set("type", "upload")
        return [field]

    @staticmethod
    def getLabels():
        return {
            "de": [
                    ("workflowstep_updateattributesfixed", "Update-Attribute behoben"),
                    ("updateattributesfixed-upload-fileatt", "Metadaten (YAML/JSON)"),
                ],
            "en": [
                    ("workflowstep_updateattributesfixed", "Update Attributes fixed"),
                    ("updateattributesfixed-upload-fileatt", "Metadata (YAML/JSON)"),
                ]
        }
