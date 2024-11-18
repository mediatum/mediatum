# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflow step simply keep processing node int this state.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import json as _json
import logging as _logging
import operator as _operator

_logg = _logging.getLogger(__name__)

import mediatumtal as _mediatumtal
import mediatumtal.tal as _

import core as _core
import utils as _utils
import utils.date as _
import utils.uwsgi as _
import workflow as _workflow


def _uwsgi_background_processing():
    for workflowstep in _core.db.query(WorkflowStep_DeferProcessing).prefetch_attrs():
        if workflowstep.settings["process"] in ("direct", "stop"):
            continue
        nodes = sorted(
            workflowstep.all_children,
            key=_operator.methodcaller("get", workflowstep.settings["timestamp-attribute"]),
        )
        if not nodes:
            continue
        try:
            workflowstep.forward(nodes[0], True)
        except:
            _logg.exception("workflowstep id %s failed to forward node %s", workflowstep.id, nodes[0].id)


def register():
    _workflow.registerStep("workflowstep_deferprocessing")
    interval = _core.config.getint("workflows.defer-processing-uwsgi-interval", 0)
    if not (interval and _utils.uwsgi.loaded):
        return
    if _utils.uwsgi.register_signal_handler_for_worker("workflow-deferprocessing")(_uwsgi_background_processing):
        raise AssertionError("failed to register uwsgi handler")
    _utils.uwsgi.add_rb_timer("workflow-deferprocessing", "workflow-deferprocessing", interval)


class WorkflowStep_DeferProcessing(_workflow.WorkflowStep):

    default_settings = {"timestamp-attribute": "updatetime", "process": "uwsgi-direct"}

    def runAction(self, node, op=""):
        node.set(self.settings["timestamp-attribute"], unicode(_utils.date.now()))
        _core.db.session.commit()
        if self.settings["process"] == "direct":
            self.forward(node, True)
        if _utils.uwsgi.loaded and self.settings["process"] == "uwsgi-direct":
            interval = _core.config.getint("workflows.defer-processing-uwsgi-interval", None)
            if interval is None:
                self.forward(node, True)


    def admin_settings_get_html_form(self, req):
        return _mediatumtal.tal.processTAL(
            dict(timestamp_attribute=self.settings["timestamp-attribute"], process=self.settings["process"]),
            file="workflow/deferprocessing.html",
            macro="workflow_step_type_config",
            request=req,
            )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert frozenset(data) == frozenset(self.default_settings)
        if data["process"] not in ("direct", "uwsgi-direct", "stop", "uwsgi-stop"):
            raise RuntimeError("bad process flag")
        if not data["timestamp-attribute"]:
            raise RuntimeError("missing attribute 'timestamp' !!!")
        self.settings = data
        _core.db.session.commit()
