# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflow step enables user to assign node.type and node.schema.
Type is stored in node.attrs[workflowstep.attrs["type-attribute"]]
and schema in node.attrs[workflowstep.attrs["schema-attribute"]].
In case of changing the node type it is not possible to change the
type of the original node, so a new node is created with the same
(system-) attributes and access rights and parents of the original node.
All files of the original node are unlinked and linked to the new
node.
If workflowstep.attrs["id-attribute"] is set, the nodeid of the new
node is stored in node.attrs[workflowstep.attrs["id-attrbute]] and the
nodeid of the original node is stored in newnode.attrs[workflowstep.attrs["id-attrbute]].
The new node is forwarded to the true step.
The original node is forwarded to the false step.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import collections as _collections

import mediatumtal.tal as _tal

import core as _core
import core.nodecache as _
import workflow as _workflow


def register():
    _workflow.registerStep("workflowstep_replacenodemetadatatype")


class WorkflowStep_ReplaceNodeMetadataType(_workflow.WorkflowStep):

    default_settings = {"type-attribute":None, "schema-attribute":None, "id-attribute":None}

    def runAction(self, node):
        nodetype = node.type
        if (self.settings["type-attribute"] is not None) and (self.settings["type-attribute"] in node.attrs):
            nodetype = node.attrs[self.settings["type-attribute"]]
        nodeschema = node.schema
        if (self.settings["schema-attribute"] is not None) and (self.settings["schema-attribute"] in node.attrs):
            nodeschema = node.attrs[self.settings["schema-attribute"]]
        metadatatypes = _core.nodecache.get_metadatatypes_node()
        if nodetype not in metadatatypes.children.filter_by(name=nodeschema).one().getDatatypes():
            raise RuntimeError("bad schema/type combination")
        if nodetype == node.type:
            node.schema = nodeschema
            _core.db.session.commit()
            self.forward(node, True)
            return
        newnode, = (cls for cls in _core.database.postgres.node.Node.get_all_subclasses()
                     if cls.__mapper__.polymorphic_identity == nodetype)
        newnode = newnode(node.name)
        _core.db.session.add(newnode)
        newnode.schema = nodeschema
        newnode.orderpos = node.orderpos
        newnode.attrs.update(node.attrs)
        newnode.system_attrs.update(node.system_attrs)
        newnode.files.extend(node.files)
        for f in tuple(node.files):
            node.files.remove(f)
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
        if self.settings["id-attribute"] is not None:
            node.attrs[self.settings["id-attribute"]] = str(newnode.id)
            newnode.attrs[self.settings["id-attribute"]] = str(node.id)
        _core.db.session.commit()
        self.forward(newnode, True)
        self.forward(node, False)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/replacenodemetadatatype.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        data["type-attribute"] = data["type-attribute"] or None
        data["schema-attribute"] = data["schema-attribute"] or None
        data["id-attribute"] = data["id-attribute"] or None
        assert frozenset(data) == frozenset(self.default_settings)
        self.settings = data
        _core.db.session.commit()
