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
import core.tree as tree
import logging
from .workflow import WorkflowStep, registerStep
from core.translation import t, lang
from schema.schema import getMetaType, VIEW_HIDE_EMPTY


def mkfilelist(node, deletebutton=0, language=None, request=None):
    return request.getTAL(
        "workflow/showdata.html", {"files": node.getFiles(), "node": node, "delbutton": deletebutton}, macro="workflow_filelist")


def mkfilelistshort(node, deletebutton=0, language=None, request=None):
    return request.getTAL(
        "workflow/showdata.html", {"files": node.getFiles(), "node": node, "delbutton": deletebutton}, macro="workflow_filelist_short")


def register():
    tree.registerNodeClass("workflowstep-showdata", WorkflowStep_ShowData)
    tree.registerNodeClass("workflowstep-wait", WorkflowStep_ShowData)
    registerStep("workflowstep-showdata")
    registerStep("workflowstep-wait")


class WorkflowStep_ShowData(WorkflowStep):

    def show_workflow_node(self, node, req):

        if "gotrue" in req.params:
            return self.forwardAndShow(node, True, req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        key = req.params.get("key", req.session.get("key", ""))
        masks = self.get("masks")
        if not masks:
            masklist = ["editmask"]
        else:
            masklist = masks.split(";")

        fieldmap = []
        mask = None
        for maskname in masklist:
            t = getMetaType(node.type)
            if t:
                if node.get('system.wflanguage') != '':  # use correct language
                    mask = t.getMask("%s.%s" % (node.get('system.wflanguage'), maskname))
                if not mask:
                    mask = t.getMask(maskname)

                try:
                    fieldmap += [mask.getViewHTML([node], VIEW_HIDE_EMPTY, language=lang(req))]
                except:
                    print "error"
                    logging.getLogger("error").error("mask %s defined for workflow step not found." % mask)
                    return ""

        filelist = ""
        filelistshort = ""

        if node.getFiles():
            filelist = mkfilelist(node, request=req)
            filelistshort = mkfilelistshort(node, request=req)

        return req.getTAL("workflow/showdata.html",
                          {"key": key,
                           "filelist": filelist,
                           "filelistshort": filelistshort,
                           "fields": fieldmap,
                           "pretext": self.getPreText(lang(req)),
                           "posttext": self.getPostText(lang(req)),
                           "sidebar": self.getSidebarText(lang(req)),
                           "buttons": self.tableRowButtons(node)},
                          macro="workflow_showdata")

    def metaFields(self, lang=None):
        field = tree.Node("masks", "metafield")
        field.set("label", t(lang, "admin_wfstep_masks_to_display"))
        field.set("type", "text")
        return [field]
