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
import utils.fileutils as _fileutils
import workflow as _workflow


def register():
    _workflow.registerStep("workflowstep_hierarchicalchoice2metafield")


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

    default_settings = {"target-attribute-name": ""}

    def show_workflow_node(self, node, req):
        if "gofalse" in req.values:
            return self.forwardAndShow(node, False, req)

        with open(_os.path.join(_core.config.get("paths.datadir"), self.files[0].path), "rb") as f:
            tree_data = _ruamel_yaml.YAML(typ="safe", pure=True).load(f)

        lang = _core.translation.set_language(req.accept_languages)

        if "gotrue" not in req.values:
            metafielderror = u""
        elif _source_has_value(tree_data, req.values["hierarchicalmetafield"]):
            node.attrs[self.settings["target-attribute-name"]] = req.values["hierarchicalmetafield"]
            if hasattr(node, "event_metadata_changed"):
                node.event_metadata_changed()
            _core.db.session.commit()
            return self.forwardAndShow(node, True, req)
        else:
            metafielderror = u"{}: {}".format(
                    _core.translation.translate(lang, "wf_target_metafield_error"),
                    req.values["hierarchicalmetafield"],
                )

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

    def admin_settings_get_html_form(self, req):
        files = tuple(f for f in self.files if f.filetype=="wfstep-hierarchicalchoice2metafield")
        if len(files) == 1:
            context = dict(
                    filebasename=files[0].base_name,
                    filesize=files[0].size,
                    fileurl=u'/file/{}/{}'.format(self.id, files[0].base_name),
                   )
        else:
            context = dict(filebasename=None, filesize=None, fileurl=None)
        context.update(self.settings)
        return _mediatumtal.tal.processTAL(
            context,
            file="workflow/hierarchicalchoice2metafield.html",
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
                                              filetype="wfstep-hierarchicalchoice2metafield"))
        assert tuple(data) == ('target-attribute-name',)
        self.settings = data
        _core.db.session.commit()
