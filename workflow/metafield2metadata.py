# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflow step enables user to assign metadata from metafield to node. Metafield is stored in
workflowstep.attrs.["source-attribute-name"] and specifies institute. Institutes contain (key-value) pairs
as metadata are stored in file attached to this workflow step in form of tree structure.
If processing node.attrs[workflowstep.attrs.["source-attribute-name"]] is found in file then its attributes
will be set or removed to these (key-value) pairs (removed in case of value is None).
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import collections as _collections
import os as _os

import ruamel.yaml as _ruamel_yaml

import core as _core
import schema.schema as _schema_schema
import workflow as _workflow


_yaml_loader = _ruamel_yaml.YAML(typ="safe", pure=True).load


def register():
    _workflow.registerStep("workflowstep_metafield2metadata")
    _core.translation.addLabels(WorkflowStep_Metafield2Metadata.getLabels())


class WorkflowStep_Metafield2Metadata(_workflow.WorkflowStep):

    def runAction(self, node, op=""):
        with open(_os.path.join(_core.config.get("paths.datadir"), self.files[0].path), "rb") as f:
            mapping = _yaml_loader(f)

        source_sep = self.attrs.get("source-metadata-separator")
        target_sep = self.attrs.get("target-metadata-separator", "")
        source_data = node.attrs[self.attrs["source-attribute-name"]]
        source_data = source_data.split(source_sep) if source_sep else [source_data]

        target_data = _collections.defaultdict(list)
        for token in source_data:
            for key, value in mapping[token].iteritems():
                target_data[key].append(value)
        for key in tuple(target_data):
            value = tuple(v for v in target_data[key] if v is not None)
            target_data[key] = target_sep.join(value) if value else None

        node.attrs.update(target_data)
        for key, value in target_data.iteritems():
            if value is None:
                del node.attrs[key]

        if hasattr(node, "event_metadata_changed"):
            node.event_metadata_changed()

        _core.db.session.commit()

        self.forward(node, True)

    def metaFields(self, lang=None):
        field = _schema_schema.Metafield("upload_fileatt")
        label = "metafield2metadata-upload-fileatt"
        field.set(
            "label",
            _core.translation.translate(lang, label) if lang else _core.translation.translate_in_request(label),
        )
        field.set("type", "upload")
        field2 = _schema_schema.Metafield("source-attribute-name")
        label = "metafield2metadata-source-attribute-name"
        field2.set(
            "label",
            _core.translation.translate(lang, label) if lang else _core.translation.translate_in_request(label),
        )
        field2.set("type", "text")
        field3 = _schema_schema.Metafield("source-metadata-separator")
        label = "metafield2metadata-source-metadata-separator"
        field3.set(
            "label",
            _core.translation.translate(lang, label) if lang else _core.translation.translate_in_request(label),
        )
        field3.set("type", "text")
        field4 = _schema_schema.Metafield("target-metadata-separator")
        label = "metafield2metadata-target-metadata-separator"
        field4.set(
            "label",
            _core.translation.translate(lang, label) if lang else _core.translation.translate_in_request(label),
        )
        field4.set("type", "text")
        return [field, field2, field3, field4]

    @staticmethod
    def getLabels():
        return dict(
            de=[
                    ("workflowstep_metafield2metadata", "Metadaten aus Metafeld generieren"),
                    ("metafield2metadata-upload-fileatt", "Metadaten (YAML/JSON)"),
                    ("metafield2metadata-source-attribute-name", "Quell-Metadatenfeld-Name"),
                    ("metafield2metadata-source-metadata-separator", "Quell-Metadaten-Trennzeichen"),
                    ("metafield2metadata-target-metadata-separator", "Ergebnis-Metadaten-Trennzeichen"),
                ],
            en=[
                    ("workflowstep_metafield2metadata", "Generate Metadata from Metafield"),
                    ("metafield2metadata-upload-fileatt", "Metadata (YAML/JSON)"),
                    ("metafield2metadata-source-attribute-name", "Source Metafield Name"),
                    ("metafield2metadata-source-metadata-separator", "Source-Metadata-Separator"),
                    ("metafield2metadata-target-metadata-separator", "Target-Metadata-Separator"),
                ]
        )
