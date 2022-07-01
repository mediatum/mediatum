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
from mediatumtal import tal as _tal
import schema.schema as _schema_schema
import utils.fileutils as _fileutils
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

    def admin_settings_get_html_form(self, req):
        files = tuple(f for f in self.files if f.filetype=="wfstep-metafield2metadata")
        if len(files) == 1:
            context = dict(
                    filebasename=files[0].base_name,
                    filesize=files[0].size,
                    fileurl=u'/file/{}/{}'.format(self.id, files[0].base_name),
                   )
        else:
            context = dict(filebasename=None, filesize=None, fileurl=None)
        context.update({
                'source-attribute-name':self.get('source-attribute-name'),
                'source-metadata-separator':self.get('source-metadata-separator'),
                'target-metadata-separator':self.get('target-metadata-separator'),
               })

        return _tal.processTAL(
            context,
            file="workflow/metafield2metadata.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        fileatt = data.pop('fileatt', None)
        if fileatt:
            for f in self.files:
                self.files.remove(f)
            self.files.append(_fileutils.importFile(_fileutils.sanitize_filename(fileatt.filename), fileatt,
                                              filetype="wfstep-metafield2metadata"))
        for attr in ('source-attribute-name', 'source-metadata-separator', 'target-metadata-separator'):
            self.set(attr, data.pop(attr))
        assert not data
        _core.db.session.commit()

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
