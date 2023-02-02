# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import flask as _flask
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
import core.translation as _core_translation
from .workflow import WorkflowStep, registerStep
from schema.schema import VIEW_HIDE_EMPTY, Metafield, Metadatatype
from core import db

q = db.query

logg = logging.getLogger(__name__)


def mkfilelist(node, deletebutton=0, language=None, request=None):
    return _tal.processTAL({"files": node.files, "node": node, "delbutton": deletebutton}, file="workflow/showdata.html", macro="workflow_filelist", request=request)


def mkfilelistshort(node, deletebutton=0, language=None, request=None):
    return _tal.processTAL({"files": node.files, "node": node, "delbutton": deletebutton}, file="workflow/showdata.html", macro="workflow_filelist_short", request=request)


def register():
    registerStep("workflowstep_showdata")


class WorkflowStep_ShowData(WorkflowStep):

    default_settings = dict(
        masks=("editmask",),
    )

    def show_workflow_node(self, node, req):

        if "gotrue" in req.params:
            return self.forwardAndShow(node, True, req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        key = req.params.get("key", _flask.session.get("key", ""))

        fieldmap = []
        mask = None
        for maskname in self.settings["masks"]:
            t = q(Metadatatype).filter_by(name=node.schema).scalar()
            if t:
                if node.get('system.wflanguage') != '':  # use correct language
                    mask = t.getMask("%s.%s" % (node.get('system.wflanguage'), maskname))
                if not mask:
                    mask = t.getMask(maskname)

                try:
                    fieldmap.append(mask.getViewHTML(
                            [node],
                            VIEW_HIDE_EMPTY,
                            language=_core_translation.set_language(req.accept_languages),
                        ))
                except:
                    logg.exception("exception for mask %s, returning empty string", mask)
                    return ""

        filelist = ""
        filelistshort = ""

        if node.files:
            filelist = mkfilelist(node, request=req)
            filelistshort = mkfilelistshort(node, request=req)

        return _tal.processTAL(
                dict(
                    key=key,
                    filelist=filelist,
                    filelistshort=filelistshort,
                    fields=fieldmap,
                    pretext=self.getPreText(_core_translation.set_language(req.accept_languages)),
                    posttext=self.getPostText(_core_translation.set_language(req.accept_languages)),
                    buttons=self.tableRowButtons(node),
                    csrf=_core_csrfform.get_token(),
                ),
                file="workflow/showdata.html",
                macro="workflow_showdata",
                request=req,
            )
    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/showdata.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        assert tuple(data) == ("masks",)
        masks = (m.strip() for m in data["masks"].split("\r\n"))
        self.settings = dict(masks=filter(None, masks))
        db.session.commit()
