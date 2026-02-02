# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflowstep searches nodes for specified criteria.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import itertools as _itertools
import logging as _logging
import operator as _operator
import os as _os

import mediatumtal as _mediatumtal
import mediatumtal.tal as _
import ruamel as _ruamel
import ruamel.yaml as _

import core as _core
import core.config as _
import core.database.postgres.node as _
import utils as _utils
import utils.fileutils as _
import workflow as _workflow

_logg = _logging.getLogger(__name__)


def register():
    _workflow.registerStep("workflowstep_searchnode")


class WorkflowStep_SearchNode(_workflow.WorkflowStep):

    default_settings = {
            'target-metafield':'',
            'root-id-metafield': '',
            'type-match-metafield': None,
            'schema-match-metafield': None,
            'name-match-metafield': None,
           }

    def runAction(self, node, op=""):
        if self.files:
            with open(_os.path.join(_core.config.get("paths.datadir"), self.files[0].path), "rb") as f:
                metafields = _ruamel.yaml.YAML(typ="safe", pure=True).load(f)
        else:
            metafields = {}
        query = int(node.attrs[self.settings["root-id-metafield"]])
        query = _core.db.query(_core.database.postgres.node.Node).get(query).all_children
        for column in ("type", "name", "schema"):
            fieldname = self.settings["{}-match-metafield".format(column)]
            if (fieldname is not None) and (fieldname in node.attrs):
                query = query.filter_by(**{column:node.attrs[fieldname]})
        for src_metafield, dest_metafield in metafields.iteritems():
            if src_metafield in node.attrs:
                query = query.filter(_core.database.postgres.node.Node.attrs[dest_metafield].astext == node.attrs[src_metafield])
        node.attrs[self.settings["target-metafield"]] = " ".join(map(str, map(_operator.attrgetter("id"), query.all())))
        _core.db.session.commit()
        self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        files = tuple(f for f in self.files if f.filetype=="wfstep-searchnode")
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
                file="workflow/searchnode.html",
                macro="workflow_step_type_config",
                request=req,
            )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        match_metafields = data.pop('match-metafields', None)
        if data.pop('match-metafields-delete', None) or match_metafields:
            for f in self.files:
                self.files.remove(f)
        if match_metafields:
            self.files.append(_utils.fileutils.importFile(
                _utils.fileutils.sanitize_filename(match_metafields.filename),
                match_metafields,
                filetype="wfstep-searchnode",
               ))
        assert frozenset(data) == frozenset(("target-metafield", "root-id-metafield", "type-match-metafield", "schema-match-metafield", "name-match-metafield"))
        if not (data["target-metafield"] and data["root-id-metafield"]):
            raise RuntimeError("required fields missing")
        for attrname in ("name-match-metafield", "type-match-metafield", "schema-match-metafield"):
            if not data[attrname]:
                data[attrname] = None
        self.settings = data
        _core.db.session.commit()
