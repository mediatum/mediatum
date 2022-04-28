# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import flask as _flask
import mediatumtal.tal as _tal
from .workflow import WorkflowStep, registerStep
from core.translation import t, lang
from schema.schema import VIEW_HIDE_EMPTY, Metafield, Metadatatype
from core import db

q = db.query

logg = logging.getLogger(__name__)


def mkfilelist(node, deletebutton=0, language=None, request=None):
    return _tal.processTAL({"files": node.files, "node": node, "delbutton": deletebutton}, file="workflow/showdata.html", macro="workflow_filelist", request=request)


def mkfilelistshort(node, deletebutton=0, language=None, request=None):
    return _tal.processTAL({"files": node.files, "node": node, "delbutton": deletebutton}, file="workflow/showdata.html", macro="workflow_filelist_short", request=request)


def register():
    #tree.registerNodeClass("workflowstep-showdata", WorkflowStep_ShowData)
    #tree.registerNodeClass("workflowstep-wait", WorkflowStep_ShowData)
    registerStep("workflowstep_showdata")


class WorkflowStep_ShowData(WorkflowStep):

    def show_workflow_node(self, node, req):

        if "gotrue" in req.params:
            return self.forwardAndShow(node, True, req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        key = req.params.get("key", _flask.session.get("key", ""))
        masks = self.get("masks")
        if not masks:
            masklist = ["editmask"]
        else:
            masklist = masks.split(";")

        fieldmap = []
        mask = None
        for maskname in masklist:
            t = q(Metadatatype).filter_by(name=node.schema).scalar()
            if t:
                if node.get('system.wflanguage') != '':  # use correct language
                    mask = t.getMask("%s.%s" % (node.get('system.wflanguage'), maskname))
                if not mask:
                    mask = t.getMask(maskname)

                try:
                    fieldmap += [mask.getViewHTML([node], VIEW_HIDE_EMPTY, language=lang(req))]
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
                    pretext=self.getPreText(lang(req)),
                    posttext=self.getPostText(lang(req)),
                    buttons=self.tableRowButtons(node),
                    csrf=req.csrf_token.current_token,
                ),
                file="workflow/showdata.html",
                macro="workflow_showdata",
                request=req,
            )

    def metaFields(self, lang=None):
        field = Metafield("masks")
        field.set("label", t(lang, "admin_wfstep_masks_to_display"))
        field.set("type", "text")
        return [field]
