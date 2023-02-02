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
from mediatumtal import tal as _tal

import core as _core
import utils.fileutils as _fileutils
import workflow as _workflow


_yaml_loader = _ruamel_yaml.YAML(typ="safe", pure=True).load


def register():
    _workflow.registerStep("workflowstep_updateattributesfixed")


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

    def admin_settings_get_html_form(self, req):
        files = tuple(f for f in self.files if f.filetype=="wfstep-updateattributesfixed")
        if len(files) == 1:
            context = dict(
                    filebasename=files[0].base_name,
                    filesize=files[0].size,
                    fileurl=u'/file/{}/{}'.format(self.id, files[0].base_name),
                   )
        else:
            context = dict(filebasename=None, filesize=None, fileurl=None)

        return _tal.processTAL(
            context,
            file="workflow/updateattributesfixed.html",
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
                                              filetype="wfstep-updateattributesfixed"))
        assert not data
        _core.db.session.commit()
