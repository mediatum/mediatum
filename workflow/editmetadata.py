# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import flask as _flask
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
import core.translation as _core_translation
from .workflow import WorkflowStep, registerStep
from schema.schema import getMetaType
from schema.schema import Metafield
from core import db
from core.users import user_from_session as _user_from_session

q = db.query


def register():
    #tree.registerNodeClass("workflowstep-edit", WorkflowStep_EditMetadata)
    registerStep("workflowstep_editmetadata")
    _core_translation.addLabels(WorkflowStep_EditMetadata.getLabels())


class WorkflowStep_EditMetadata(WorkflowStep):

    def show_workflow_node(self, node, req):
        user = _user_from_session()
        result = ""
        error = ""
        key = req.params.get("key", _flask.session.get("key", ""))

        maskname = self.get("mask")
        mask = None
        if node.get('system.wflanguage') != '':  # use correct language
            mask = getMetaType(node.schema).getMask("%s.%s" % (node.get('system.wflanguage'), maskname))

        if not mask:
            mask = getMetaType(node.schema).getMask(maskname)

        if "metaDataEditor" in req.params:
            mask.apply_edit_update_attrs_to_node(node, mask.get_edit_update_attrs(req, user))
            db.session.commit()
            missing = mask.validate([node])
            if not missing or "gofalse" in req.params:
                op = "gotrue" in req.params
                return self.forwardAndShow(node, op, req)
            else:
                error = u'<p class="error">{}</p>'.format(
                        _core_translation.t(_core_translation.set_language(req.accept_languages), "workflow_error_msg"),
                    )
                req.params["errorlist"] = missing

        if mask:
            maskcontent = mask.getFormHTML([node], req)
        else:
            maskcontent = _tal.processTAL({}, file="workflow/editmetadata.html", macro="maskerror", request=req)

        return _tal.processTAL(
                dict(
                    name=self.name,
                    error=error,
                    key=key,
                    mask=maskcontent,
                    pretext=self.getPreText(_core_translation.set_language(req.accept_languages)),
                    posttext=self.getPostText(_core_translation.set_language(req.accept_languages)),
                    buttons=self.tableRowButtons(node),
                    csrf=_core_csrfform.get_token(),
                ),
                file="workflow/editmetadata.html",
                macro="workflow_metadateneditor",
                request=req,
            )

    def metaFields(self, lang=None):
        field = Metafield("mask")
        field.set("label", _core_translation.t(lang, "admin_wfstep_editor_mask"))
        field.setFieldtype("text")
        return [field]

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("wf_nomaskfound", "Die angebene Maske wurde nicht gefunden."),
                ],
                "en":
                [
                    ("wf_nomaskfound", "Configured Mask not found."),
                ]
                }
