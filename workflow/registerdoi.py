# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflow step enables user to contact DataCite that provides persistent identifiers (DOIs specifically)
for research data and other research outputs.
The basic operations of the DataCite REST API:
    * Retrieving a single DOI
    * Retrieving a list of DOIs
    * Creating DOIs with the REST API
    ...
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from itertools import imap as map
from itertools import ifilter as filter
range = xrange

from mediatumtal import tal as _tal

import core as _core
import workflow as _workflow
from export import doi as _export_doi


def register():
    _workflow.registerStep("workflowstep_registerdoi")


class WorkflowStep_RegisterDOI(_workflow.WorkflowStep):

    default_settings = dict(action="create", event=None, suffixattr=None, urlattr=None, mask=None)

    def runAction(self, node, op=""):
        suffix = node.get(self.settings["suffixattr"])
        if not suffix:
            raise RuntimeError("missing DOI-Suffix Attribut")
        if self.settings["urlattr"] == "" or \
                (self.settings["urlattr"] in node.attrs and node.get(self.settings["urlattr"]) == ""):
            raise RuntimeError("URL Attribut Error")

        urlattr = self.settings["urlattr"] and node.get(self.settings["urlattr"]) or None
        _export_doi.registerdoi(
            node,
            self.settings["mask"],
            urlattr,
            suffix,
            self.settings["event"],
            self.settings["action"],
            )
        self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/registerdoi.html",
            macro="workflow_step_type_config",
            request=req,
            )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert frozenset(data) == frozenset(('action', 'suffixattr', 'urlattr', 'mask', 'event'))
        if not data.get("suffixattr"):
            raise RuntimeError("missing DOI-Suffix Attribut")
        data["event"] = None if data["event"]=="none" else data["event"]
        data["mask"] =  data["mask"] or None
        data["urlattr"] =  data["urlattr"] or None
        self.settings = data
        _core.db.session.commit()
