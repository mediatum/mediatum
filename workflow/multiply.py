# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflow step multiplies the current node depending on the content of the attribute `split-attribute`
The attribute `split-attribute` must exists of the current node otherwise a RuntimeError is raised.
If the attribute `split-attribute` is empty the current node is unlinked from the workflow
For every entry except the first one in the attribute `split-attribute` separated by spaces a new node
is created which is clone of the current node.
The first entry is reserved for the current node, the remaining entries are distrubuted to the new create
node.
All new created nodes are linked under the same parents as the current nodes.
All files of the current nodes where copied to the new nodes.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import itertools as _itertools
import json as _json
import logging as _logging

import mediatumtal as _mediatumtal
import mediatumtal.tal as _

import core as _core
import core.config as _
import utils as _utils
import utils.fileutils as _
import workflow as _workflow

_logg = _logging.getLogger(__name__)


def register():
    _workflow.registerStep("workflowstep_multiply")


class WorkflowStep_Multiply(_workflow.WorkflowStep):

    default_settings = {'split-attribute': None, 'fileid-map-attribute': None}

    def runAction(self, node, op=""):
        values = node.attrs[self.settings['split-attribute']].split()
        if not values:
            for parent in tuple(node.parents):
                parent.children.remove(node)
            _core.db.session.commit()
            return
        node.attrs[self.settings['split-attribute']] = values.pop()
        if self.settings['fileid-map-attribute']:
            node.attrs[self.settings['fileid-map-attribute']] = _json.dumps({f.id:f.id for f in node.files})
        newnodes = []
        for value in values:
            file_id_mapping = {}
            newnode = _core.database.postgres.node.Node(node.name)
            _core.db.session.add(newnode)
            newnode.type = node.type
            newnode.schema = node.schema
            newnode.orderpos = node.orderpos
            newnode.attrs.update(node.attrs)
            newnode.system_attrs.update(node.system_attrs)
            newnode.attrs[self.settings['split-attribute']] = value
            for f in node.files:
                with f.open('rb', encoding=None) as file:
                    newnode.files.append(_utils.fileutils.importFile(f.base_name, file, f.filetype))
                newnode.files[-1].mimetype = f.mimetype
                file_id_mapping[str(f.id)] = newnode.files[-1].id
            if self.settings['fileid-map-attribute']:
                newnode.attrs[self.settings['fileid-map-attribute']] = _json.dumps(file_id_mapping)
            for parent in node.parents:
                parent.children.append(newnode)
            for access_ruleset in node.access_ruleset_assocs:
                if access_ruleset.private:
                    ruleset = newnode.get_or_add_special_access_ruleset(ruletype=access_ruleset.ruletype)
                    for rule_assoc in access_ruleset.ruleset.rule_assocs:
                        ruleset.rule_assocs.append(_core.database.postgres.permission.AccessRulesetToRule(rule=rule_assoc.rule))
                else:
                    newnode.access_ruleset_assocs.append(_core.database.postgres.permission.NodeToAccessRuleset(
                        ruleset_name=access_ruleset.ruleset_name,
                        ruletype=access_ruleset.ruletype,
                        invert=access_ruleset.invert,
                        blocking=access_ruleset.blocking,
                        private=access_ruleset.private,
                       ))
            newnodes.append(newnode)
        _core.db.session.commit()
        newnodes.append(node)
        for newnode in newnodes:
            self.forward(newnode, True)

    def admin_settings_get_html_form(self, req):
        return _mediatumtal.tal.processTAL(
                self.settings,
                file="workflow/multiply.html",
                macro="workflow_step_type_config",
                request=req,
            )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert tuple(data) == ("split-attribute", "fileid-map-attribute")
        assert data["split-attribute"]
        if not data["fileid-map-attribute"]:
            data["fileid-map-attribute"] = None
        self.settings = data
        _core.db.session.commit()
