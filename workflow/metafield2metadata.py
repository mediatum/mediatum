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
import utils.fileutils as _fileutils
import workflow as _workflow


def register():
    _workflow.registerStep("workflowstep_metafield2metadata")


class WorkflowStep_Metafield2Metadata(_workflow.WorkflowStep):

    default_settings = {
            'source-attribute-name':"",
            'source-metadata-separator':"",
            'target-metadata-separator':"",
           }

    def runAction(self, node, op=""):
        with open(_os.path.join(_core.config.get("paths.datadir"), self.files[0].path), "rb") as f:
            mapping = _ruamel_yaml.YAML(typ="safe", pure=True).load(f)

        source_sep = self.settings["source-metadata-separator"]
        target_sep = self.settings["target-metadata-separator"]
        source_data = node.attrs[self.settings["source-attribute-name"]]
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
        context.update(self.settings)
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
        assert frozenset(data) == frozenset(('source-attribute-name', 'source-metadata-separator', 'target-metadata-separator'))
        self.settings = data
        _core.db.session.commit()
