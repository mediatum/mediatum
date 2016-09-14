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
from .workflow import WorkflowStep, registerStep
from core.translation import t, lang, addLabels
from schema.schema import getMetaType
from schema.schema import Metafield
from core import db
from core.transition import current_user

q = db.query


def register():
    #tree.registerNodeClass("workflowstep-edit", WorkflowStep_EditMetadata)
    registerStep("workflowstep_editmetadata")
    addLabels(WorkflowStep_EditMetadata.getLabels())


class WorkflowStep_EditMetadata(WorkflowStep):

    def show_workflow_node(self, node, req):
        result = ""
        error = ""
        key = req.params.get("key", req.session.get("key", ""))

        maskname = self.get("mask")
        mask = None
        if node.get('system.wflanguage') != '':  # use correct language
            mask = getMetaType(node.schema).getMask("%s.%s" % (node.get('system.wflanguage'), maskname))

        if not mask:
            mask = getMetaType(node.schema).getMask(maskname)

        if "metaDataEditor" in req.params:
            mask.update_node(node, req, current_user)
            db.session.commit()
            missing = mask.validate([node])
            if not missing or "gofalse" in req.params:
                op = "gotrue" in req.params
                return self.forwardAndShow(node, op, req)
            else:
                error = '<p class="error">%s</p>' % (t(lang(req), "workflow_error_msg"))
                req.params["errorlist"] = missing

        if mask:
            maskcontent = mask.getFormHTML([node], req)
        else:
            maskcontent = req.getTAL("workflow/editmetadata.html", {}, macro="maskerror")

        return req.getTAL("workflow/editmetadata.html",
                          {"name": self.name,
                           "error": error,
                           "key": key,
                           "mask": maskcontent,
                           "pretext": self.getPreText(lang(req)),
                           "posttext": self.getPostText(lang(req)),
                           "sidebartext": self.getSidebarText(lang(req)),
                           "buttons": self.tableRowButtons(node)},
                          macro="workflow_metadateneditor")

    def metaFields(self, lang=None):
        field = Metafield("mask")
        field.set("label", t(lang, "admin_wfstep_editor_mask"))
        field.set("type", "text")
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
