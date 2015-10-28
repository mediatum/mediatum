"""
 mediatum - a multimedia content repository

 Copyright (C) 2013 Arne Seifert <arne.seifert@tum.de>

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

import logging
from .workflow import WorkflowStep, registerStep
from core.translation import t, lang, addLabels
from schema.schema import getMetaType, VIEW_HIDE_EMPTY
from schema.schema import Metafield, Metadatatype
from core.database.postgres.permission import NodeToAccessRuleset
from core import db

q = db.query

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-fileattachment", WorkflowStep_FileAttachment)
    registerStep("workflowstep_fileattachment")
    addLabels(WorkflowStep_FileAttachment.getLabels())


class WorkflowStep_FileAttachment(WorkflowStep):

    def show_workflow_node(self, node, req):
        # print req.params

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
            maskdata = mask.getViewHTML([node], VIEW_HIDE_EMPTY, language=lang(req))
        except:
            logg.exception("exception in workflow step fileAttachment, getViewHTML failed, empty string")
            maskdata = ""

        return req.getTAL("workflow/fileattachment.html",
                          {"buttons": buttons,
                           "files": self.files,
                           "wfnode": self,
                           "pretext": self.getPreText(lang(req)),
                           "posttext": self.getPostText(lang(req)),
                           "sidebar": self.getSidebarText(lang(req)),
                           'maskdata': maskdata},
                          macro="fileattachment_show_node")

    def metaFields(self, lang=None):
        field = Metafield("upload_fileatt")
        field.set("label", t(lang, "workflowstep-fileatt_label_upload_file"))
        field.set("type", "upload")
        field2 = Metafield("mask_fileatt")
        field2.set("label", t(lang, "workflowstep-fileatt_label_mask"))
        field2.set("type", "text")
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
