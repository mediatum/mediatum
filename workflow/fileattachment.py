# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
import core.translation as _core_translation
from .workflow import WorkflowStep, registerStep
from schema.schema import getMetaType, VIEW_HIDE_EMPTY
from schema.schema import Metafield, Metadatatype
from core.database.postgres.permission import NodeToAccessRuleset
from core import db

q = db.query

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-fileattachment", WorkflowStep_FileAttachment)
    registerStep("workflowstep_fileattachment")
    _core_translation.addLabels(WorkflowStep_FileAttachment.getLabels())


class WorkflowStep_FileAttachment(WorkflowStep):

    def show_workflow_node(self, node, req):
        # set access for download same as edit (only once needed)
        for r in self.access_ruleset_assocs.filter_by(ruletype='write'):
            if self.access_ruleset_assocs.filter_by(ruleset_name=r.ruleset_name, ruletype='data').first() is None:
                self.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r.ruleset_name, ruletype='data'))
                db.session.commit()

        if "gotrue" in req.params:
            return self.forwardAndShow(node, True, req)
        elif "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        if self.getTrueLabel(language=node.get("system.wflanguage")) == "" and self.getFalseLabel(
                language=node.get("system.wflanguage")) == "":
            buttons = []
        else:
            buttons = self.tableRowButtons(node)

        try:
            mask = q(Metadatatype).filter_by(name=node.schema).one().getMask(self.get("mask_fileatt"))
            maskdata = mask.getViewHTML(
                    [node],
                    VIEW_HIDE_EMPTY,
                    language=_core_translation.set_language(req.accept_languages),
                )
        except:
            logg.exception("exception in workflow step fileAttachment, getViewHTML failed, empty string")
            maskdata = ""

        return _tal.processTAL(
                dict(
                    buttons=buttons,
                    files=self.files,
                    wfnode=self,
                    pretext=self.getPreText(_core_translation.set_language(req.accept_languages)),
                    posttext=self.getPostText(_core_translation.set_language(req.accept_languages)),
                    maskdata=maskdata,
                    csrf=_core_csrfform.get_token(),
                ),
                file="workflow/fileattachment.html",
                macro="fileattachment_show_node",
                request=req,
            )

    def metaFields(self, lang=None):
        field = Metafield("upload_fileatt")
        field.set("label", _core_translation.t(lang, "workflowstep-fileatt_label_upload_file"))
        field.setFieldtype("upload")
        field2 = Metafield("mask_fileatt")
        field2.set("label", _core_translation.t(lang, "workflowstep-fileatt_label_mask"))
        field2.setFieldtype("text")
        return [field, field2]

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-fileattachment", "Dateianhang"),
                    ("workflowstep-fileatt_label_upload_file", "Dateianhang"),
                    ("workflowstep-fileatt_label_mask", "Maskenname (optional)"),
                ],
                "en":
                [
                    ("workflowstep-fileattachment", "File-Attachment"),
                    ("workflowstep-fileatt_label_upload_file", "Attachment"),
                    ("workflowstep-fileatt_label_mask", "Maskname (optional)"),
                ]
                }
