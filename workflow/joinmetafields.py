# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Implements the workflow step class `JoinMetafields`.
This class simply takes the contents of several
(admin-defined) metafields and concatenates them,
optionally with a separater string in between.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import itertools as _itertools

from mediatumtal import tal as _tal

import core as _core
import workflow as _workflow


def register():
    _workflow.registerStep("workflowstep_joinmetafields")


class WorkflowStep_JoinMetafields(_workflow.WorkflowStep):

    default_settings = dict(
            source_metafieldnames=(),
            ignore_missing=False,
            source_separator="",
            ignore_empty=False,
            unique_values=False,
            target_separator="",
            target_metafieldname="",
        )

    def runAction(self, node, op=""):
        values = tuple(map(node.attrs.get, self.settings["source_metafieldnames"]))
        if (None in values) and not self.settings["ignore_missing"]:
            raise RuntimeError("Node {} does not have all value names {}".format(node.id,  self.settings["source_metafieldnames"]))
        # we have to keep empty strings here!
        values = (v for v in values if v is not None)
        srcsep = self.settings["source_separator"]
        if srcsep is not None:
            values = _itertools.chain.from_iterable(v.split(srcsep) for v in values)
        if self.settings["ignore_empty"]:
            values = filter(None, values)
        if self.settings["unique_values"]:
            values = frozenset(values)
        values = self.settings["target_separator"].join(values)
        node.attrs[self.settings["target_metafieldname"]] = values
        _core.db.session.commit()
        self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
                self.settings,
                file="workflow/joinmetafield.html",
                macro="workflow_step_type_config",
                request=req,
            )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        self.settings = dict(
                source_metafieldnames=data.pop("source_metafieldnames").split("\r\n"),
                ignore_missing=bool(data.pop("ignore_missing", False)),
                source_separator=data.pop("source_separator") or None,
                ignore_empty=bool(data.pop("ignore_empty", False)),
                unique_values=bool(data.pop("unique_values", False)),
                target_separator=data.pop("target_separator"),
                target_metafieldname=data.pop("target_metafieldname"),
            )
        assert not data
        _core.db.session.commit()
