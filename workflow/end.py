# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import mediatumtal.tal as _tal

import core as _core
from .workflow import WorkflowStep, registerStep
from utils.date import now

logg = logging.getLogger(__name__)


def register():
    registerStep("workflowstep_end")


class WorkflowStep_End(WorkflowStep):

    default_settings = dict(
        endremove=False,
        endsetupdatetime=False,
        endtext=None,
        interactive=True,
    )

    def show_workflow_node(self, node, req):
        if not self.settings["interactive"]:
            raise RuntimeError("cannot show non-interactive end step")
        if self.settings["endremove"]:
            # remove obj from workflownode
            self.children.remove(node)
            _core.db.session.commit()
        if self.settings["endtext"] is not None:
            link = u"/pnode?id={}&key={}".format(node.id, node.get("key"))
            link2 = u"/node?id={}".format(node.id)

            return _tal.processTAL({"node": node, "link": link, "link2": link2}, string=self.settings["endtext"], macro=None, request=req)
        return _tal.processTAL(
                dict(node=unicode(node.id)),
                """
                    <p><a href="/publish" i18n:translate="back" class="mediatum-link-mediatum"> </a></p>
                    <h2 i18n:translate="wf_step_ready"> </h2>
                    <p>&nbsp;</p>
                    <p i18n:translate="workflow_step_ready_msg"><span tal:content="node" i18n:name="name"/></p>
                """,
                macro=None,
                request=req,
            )

    def runAction(self, node):
        if self.settings["endsetupdatetime"] and node.get('updatetime') <= unicode(now()):
            node.set('updatetime', unicode(now()))
        if self.settings["endremove"] and not self.settings["interactive"]:
            self.children.remove(node)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/end.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        for attr in ('endremove', 'endsetupdatetime', 'interactive'):
            data[attr] = bool(data.get(attr))
        data["endtext"] = data["endtext"] or None
        assert frozenset(data) == frozenset(self.default_settings)
        self.settings = data
        _core.db.session.commit()
