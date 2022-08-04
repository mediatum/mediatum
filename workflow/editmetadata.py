# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import json as _json

import flask as _flask
import mediatumtal.tal as _tal

import core as _core
import core.csrfform as _core_csrfform
import core.translation as _core_translation
from .workflow import WorkflowStep, registerStep
import schema.schema as _schema
from schema.schema import getMetaType
from core.users import user_from_session as _user_from_session
import utils.utils as _utils


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

        if "mediatum-workflow-editmetadata-keyinput" in req.values:
            if node.get("system.wfstep-editmetadata.key") == req.values["mediatum-workflow-editmetadata-keyinput"]:
                node.system_attrs.pop("wfstep-editmetadata.key")
                return self.forwardAndShow(node, True, req)
        if "metaDataEditor" in req.params:
            if "gofalse" in req.params:
                return self.forwardAndShow(node, False, req)
            attrs = mask.get_edit_update_attrs(req, user)
            if attrs.errors:
                errors = {_schema.sanitize_metafield_name(name):error.get_translated_message() for name,error in attrs.errors.iteritems()}
                return '<div id="mediatum-workflow-editmetadata-fielderrors">{}</div>'.format(_utils.esc(_json.dumps(errors)))
            mask.apply_edit_update_attrs_to_node(node, attrs)
            key = _utils.gen_secure_token(64).upper()
            node.set("system.wfstep-editmetadata.key", key)
            _core.db.session.commit()
            return '<div id="mediatum-workflow-editmetadata-submitkey">{}</div>'.format(key)

        if mask:
            maskcontent = mask.getFormHTML([node], req)
        else:
            maskcontent = _tal.processTAL({}, file="workflow/editmetadata.html", macro="maskerror", request=req)

        return _tal.processTAL(
                dict(
                    name=self.name,
                    error=error,
                    idstr=self.id,
                    key=key,
                    mask=maskcontent,
                    obj=node.id,
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
        _core.db.session.commit()
