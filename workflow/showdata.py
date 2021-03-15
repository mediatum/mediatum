"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import division

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

        return _tal.processTAL({"key": key,
                                "filelist": filelist,
                                "filelistshort": filelistshort,
                                "fields": fieldmap,
                                "pretext": self.getPreText(lang(req)),
                                "posttext": self.getPostText(lang(req)),
                                "sidebar": self.getSidebarText(lang(req)),
                                "buttons": self.tableRowButtons(node),
                                "csrf": req.csrf_token.current_token, }, file="workflow/showdata.html",
                               macro="workflow_showdata", request=req)

    def metaFields(self, lang=None):
        field = Metafield("masks")
        field.set("label", t(lang, "admin_wfstep_masks_to_display"))
        field.set("type", "text")
        return [field]
