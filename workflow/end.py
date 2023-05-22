# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import mediatumtal.tal as _tal

import core.translation as _core_translation
from .workflow import WorkflowStep, registerStep
from utils.date import now
from schema.schema import Metafield
from core import db

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-end", WorkflowStep_End)
    registerStep("workflowstep_end")
    _core_translation.addLabels(WorkflowStep_End.getLabels())


class WorkflowStep_End(WorkflowStep):

    default_settings = dict(
        endremove=False,
        endsetupdatetime=False,
        endtext=None,
    )

    def show_workflow_node(self, node, req):

        if self.settings["endremove"]:
            # remove obj from workflownode
            self.children.remove(node)

        db.session.commit()
        if self.settings["endtext"] is not None:
            link = u"/pnode?id={}&key={}".format(node.id, node.get("key"))
            link2 = u"/node?id={}".format(node.id)

            return _tal.processTAL({"node": node, "link": link, "link2": link2}, string=self.settings["endtext"], macro=None, request=req)
        return _tal.processTAL({"node": unicode(node.id)}, '<p><a href="/publish" i18n:translate="workflow_back">TEXT</a></p><h2 i18n:translate="wf_step_ready">Fertig</h2><p>&nbsp;</p><p i18n:translate="workflow_step_ready_msg">Das Objekt <span tal:content="node" i18n:name="name"/> ist am Ende des Workflows angekommen.</p>', macro=None, request=req)

    def runAction(self, node, op=""):
        if self.settings["endsetupdatetime"]:
            # insert node into searchindex
            try:
                if node.get('updatetime') <= unicode(now()):  # do only if date in the past
                    node.set('updatetime', unicode(now()))
                db.session.commit()
            except:
                logg.exception("exception in workflow step end, runAction failed")

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/end.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        for attr in ('endremove', 'endsetupdatetime'):
            data[attr] = bool(data.get(attr))
        data["endtext"] = data["endtext"] or None
        assert frozenset(data) == frozenset(("endremove", "endsetupdatetime", "endtext"))
        self.settings = data
        db.session.commit()

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-end", "Endknoten"),
                    ("admin_wfstep_endtext", "Textseite"),
                    ("admin_wfstep_endremove", "Entferne aus Workflow"),
                    ("admin_wfstep_endsetupdatetime", "Setze Aktualisierungszeit"),
                ],
                "en":
                [
                    ("workflowstep-end", "End node"),
                    ("admin_wfstep_endtext", "Text Page"),
                    ("admin_wfstep_endremove", "Remove from Workflow"),
                    ("admin_wfstep_endsetupdatetime", "set updatetime"),
                ]
                }
