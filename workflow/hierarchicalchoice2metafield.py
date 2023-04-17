# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflow step enables user to assign an institute to a document as node in Database
The hierarchical structure of institutes is stored in file attached to this workflow step
and it is presented to user in form of a selection tree. Fieldname for institute is stored
in workflowstep.attrs["target-attribute-name"]] and selected institute is stored in
node.attrs[workflowstep.attrs["target-attribute-name"]].
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import os as _os
import json as _json
import cgi as _cgi

import mediatumtal as _mediatumtal
import ruamel.yaml as _ruamel_yaml

import core as _core
import core.csrfform as _core_csrfform
import schema.schema as _schema_schema
import workflow as _workflow


_yaml_loader = _ruamel_yaml.YAML(typ="safe", pure=True).load


def register():
    _workflow.registerStep("workflowstep_hierarchicalchoice2metafield")
    _core.translation.addLabels(WorkflowStep_HierarchicalChoice2Metafield.getLabels())


def _make_fancytree_source(options_tree):
    """
    Convert a structure given by a simple dict-nesting
    into a fance-tree-compatible structure.

    Given (here as YAML):
    - A:
        - B: b
        - C: c
    - D: d

    the function returns (here as YAML):

    children:
    - children:
        - {key: c, title: C}
        - {key: b, title: B}
      title: A
    -   {key: d, title: D}

    :param data: data loaded from YAML-file
    :param fancytree_dict: init dict in fancytree format
    :return: fancytree source format
    """
    children = list()
    for entry in options_tree:
        entry, = entry.iteritems()
        title, value = entry
        if isinstance(value, str):
            child = dict(title=title, key=value)
        else:
            child = _make_fancytree_source(value)
            child["title"] = title
        children.append(child)
    return dict(children=children)


def _source_has_value(options_tree, value):
    assert isinstance(value, (str, unicode))
    for entry in options_tree:
        entry, = entry.iteritems()
        entry = entry[1]
        if (entry == value) or (not isinstance(entry, str) and _source_has_value(entry, value)):
            return True


class WorkflowStep_HierarchicalChoice2Metafield(_workflow.WorkflowStep):

    def show_workflow_node(self, node, req):
        if "gofalse" in req.values:
            return self.forwardAndShow(node, False, req)

        with open(_os.path.join(_core.config.get("paths.datadir"), self.files[0].path), "rb") as f:
            tree_data = _yaml_loader(f)

        lang = _core.translation.set_language(req.accept_languages)

        if "gotrue" not in req.values:
            metafielderror = u""
        elif _source_has_value(tree_data, req.values["hierarchicalmetafield"]):
            node.attrs[self.attrs["target-attribute-name"]] = req.values["hierarchicalmetafield"]
            if hasattr(node, "event_metadata_changed"):
                node.event_metadata_changed()
            _core.db.session.commit()
            return self.forwardAndShow(node, True, req)
        else:
            metafielderror = u"{}: {}".format(self.getLabels()[lang][3][1], req.values["hierarchicalmetafield"])

        fancytree_source = _json.dumps(_make_fancytree_source(tree_data))

        return _mediatumtal.tal.processTAL(dict(
                node=node,
                wfstep=self,
                lang=lang,
                pretext=self.getPreText(lang),
                posttext=self.getPostText(lang),
                csrf=_core_csrfform.get_token(),
                fancytree_source=_cgi.escape(fancytree_source),
                metafielderror=metafielderror,
            ),
            file="workflow/hierarchicalchoice2metafield.html",
            macro="workflow_hierarchicalchoice2metafield",
            request=req,
        )

    def metaFields(self, lang=None):
        field = _schema_schema.Metafield("upload_fileatt")
        label = "hierarchicalchoice-upload-fileatt"
        field.set(
            "label",
            _core.translation.translate(lang, label) if lang else _core.translation.translate_in_request(label),
        )
        field.set("type", "upload")
        field2 = _schema_schema.Metafield("target-attribute-name")
        label = "hierarchicalchoice-target-attribute-name"
        field2.set(
            "label",
            _core.translation.translate(lang, label) if lang else _core.translation.translate_in_request(label),
        )
        field2.set("type", "text")
        return [field, field2]

    @staticmethod
    def getLabels():
        return dict(
            de=[
                    ("workflowstep_hierarchicalchoice2metafield", "hierarchische Auswahl"),
                    ("hierarchicalchoice-upload-fileatt", "Hierarchie (JSON/YAML)"),
                    ("hierarchicalchoice-target-attribute-name", "Ziel-Metafeld"),
                    ("wf_target_metafield_error", "Ziel-Metafeld nicht gefunden"),
                ],
            en=[
                    ("workflowstep_hierarchicalchoice2metafield", "hierarchical choice"),
                    ("hierarchicalchoice-upload-fileatt", "Hierarchy (JSON/YAML)"),
                    ("hierarchicalchoice-target-attribute-name", "Target-Metafield"),
                    ("wf_target_metafield_error", "Target-Metafield not found"),
                ],
        )
