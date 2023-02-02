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
from core import db
from core.users import user_from_session as _user_from_session

q = db.query


def register():
    registerStep("workflowstep_editmetadata")


class WorkflowStep_EditMetadata(WorkflowStep):

    default_settings = dict(
        mask="",
    )

    def show_workflow_node(self, node, req):
        user = _user_from_session()
        result = ""
        error = ""
        key = req.params.get("key", _flask.session.get("key", ""))

        mask = None
        if node.get('system.wflanguage') != '':  # use correct language
            mask = getMetaType(node.schema).getMask("{}.{}".format(node.get('system.wflanguage'), self.settings["mask"]))

        if not mask:
            mask = getMetaType(node.schema).getMask(self.settings["mask"])

        if "metaDataEditor" in req.params:
            mask.apply_edit_update_attrs_to_node(node, mask.get_edit_update_attrs(req, user))
            db.session.commit()
            missing = mask.validate([node])
            if not missing or "gofalse" in req.params:
                op = "gotrue" in req.params
                return self.forwardAndShow(node, op, req)
            else:
                error = u'<p class="error">{}</p>'.format(_core_translation.translate(
                        _core_translation.set_language(req.accept_languages),
                        "workflow_error_msg",
                    ))
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

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/editmetadata.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert tuple(data) == ("mask",)
        self.settings = data
        db.session.commit()
