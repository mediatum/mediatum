# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflowstep accesses not only the current node, but also other nodes, where the
node ids of the other nodes are defined in the attribute `node-id-attribute` of the current node
All other nodes are linked under the current workflowstep except they are linked under another workflowstep.
If some other nodes linked under another workflowstep the behaviour depends on the value of the
attribute `replace-assignment`.
It the attribute `replace-assignment` is set to True these nodes are unlinked from the other workflowstep.
It the attribute `replace-assignment` is set to False these nodes are ignored.
The content of the attribute name of the current-node is then stored in the attribute name of the other nodes.
It the attribute name of the current-node does not exists the attribute of the other node is deleted but only
if the attribute `metafield-purge-missing` of the current node is set to True.
All other nodes are moved in the workflow to the True-branch of the current workflowstep.
The current node is moved to the False-branch of the current workflowstep.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import itertools as _itertools
import os as _os

import mediatumtal as _mediatumtal
import mediatumtal.tal as _

import contenttypes as _contenttypes
import core as _core
import core.config as _
import core.database.postgres.node as _
import utils as _utils
import utils.fileutils as _
import workflow as _workflow

import logging as _logging
_logg = _logging.getLogger(__name__)


def register():
    _workflow.registerStep("workflowstep_addnode")


class WorkflowStep_AddNode(_workflow.WorkflowStep):

    default_settings = {
            'node-id-attribute':'',
            'replace_assignment': False,
            'copy-metafield-attribute': None,
           }

    def runAction(self, node, op=""):
        nodes = node.attrs.get(self.settings["node-id-attribute"]).split()
        nodes = map(int, nodes)
        nodes = tuple(map(_core.db.query(_core.database.postgres.node.Node).get, nodes))
        if not all(isinstance(n, _contenttypes.Content) for n in nodes):
            raise RuntimeError("bad node type")
        if self.settings["replace_assignment"]:
            for newnode in nodes:
                workflow_step = _workflow.getNodeWorkflowStep(newnode)
                if workflow_step:
                    workflow_step.children.remove(newnode)
        else:
            nodes = tuple(_itertools.ifilterfalse(_workflow.getNodeWorkflowStep, nodes))

        self.children.extend(nodes)
        copy_metafield = self.settings["copy-metafield-attribute"]
        if copy_metafield:
            for newnode in nodes:
                if copy_metafield in node.attrs:
                    newnode.attrs[copy_metafield] = node.attrs[copy_metafield]
                else:
                    newnode.attrs.pop(copy_metafield, None)

        _core.db.session.commit()
        for newnode in nodes:
            self.forward(newnode, True)
        self.forward(node, False)

    def admin_settings_get_html_form(self, req):
        return _mediatumtal.tal.processTAL(
                self.settings,
                file="workflow/addnode.html",
                macro="workflow_step_type_config",
                request=req,
            )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        data['replace_assignment'] = bool(data.get('replace_assignment'))
        assert tuple(data) == ("node-id-attribute", "replace_assignment", "copy-metafield-attribute")
        self.settings = data
        _core.db.session.commit()
