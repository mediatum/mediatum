"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Peter Heckl <heckl@ub.tum.de>

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
from workflow import WorkflowStep, registerStep
import utils.fileutils as fileutils
from utils.utils import OperationException
from showdata import mkfilelist, mkfilelistshort
from core.translation import t,lang
import os

def register():
    tree.registerNodeClass("workflowstep-upload", WorkflowStep_Upload)
    registerStep("workflowstep-upload")

class WorkflowStep_Upload(WorkflowStep):

    def show_workflow_node(self, node, req):
        error = ""

        for key in req.params.keys():
            if key.startswith("delete_"):
                filename = key[7:-2]
                all = 0
                for file in node.getFiles():
                    if file.getName()==filename:
                        if file.type in ['document', 'image']: # original -> delete all
                            all = 1
                        node.removeFile(file)

                if all==1: # delete all files
                    for file in node.getFiles():
                        node.removeFile(file)

        if "file" in req.params:
            file = req.params["file"]
            if not file:
                error = t(req, "workflowstep_file_not_uploaded")
            else:
                del req.params["file"]
                fileExtension = os.path.splitext(file.filename)[1][1:].strip().lower()

                if fileExtension in self.get("limit").lower().split(";") or self.get("limit").strip() in ['*', '']:
                    orig_filename = file.filename
                    if hasattr(file,"filename") and file.filename:
                        file = fileutils.importFile(file.filename,file.tempname)
                        node.addFile(file)
                        node.setName(orig_filename)
                        if hasattr(node,"event_files_changed"):
                            try:
                                node.event_files_changed()
                            except OperationException, ex:
                                error = ex.value
                else:
                    error = t(req, "WorkflowStep_InvalidFileType")


        if "gotrue" in req.params:
            if hasattr(node,"event_files_changed"):
                node.event_files_changed()
            if len(node.getFiles())>0:
                return self.forwardAndShow(node, True, req)
            elif not error:
                error = t(req, "no_file_transferred")

        if "gofalse" in req.params:
            if hasattr(node,"event_files_changed"):
                node.event_files_changed()
            #if len(node.getFiles())>0:
            return self.forwardAndShow(node, False, req)
            #else:
            #    error = t(req, "no_file_transferred")

        filelist = mkfilelist(node, 1, request=req)
        filelistshort = mkfilelistshort(node, 1, request=req)

        return req.getTAL("workflow/upload.html", {"obj": node.id, "id": self.id,"prefix": self.get("prefix"), "suffix": self.get("suffix"), "limit": self.get("limit"), "filelist": filelist, "filelistshort":filelistshort, "node": node, "buttons": self.tableRowButtons(node),"singlefile":self.get('singleobj'), "error":error, "pretext":self.getPreText(lang(req)), "posttext":self.getPostText(lang(req))}, macro="workflow_upload")

    def metaFields(self, lang=None):
        ret = list()
        field = tree.Node("prefix", "metafield")
        field.set("label", t(lang, "admin_wfstep_text_before_upload_form"))
        field.set("type", "memo")
        ret.append(field)

        field = tree.Node("suffix", "metafield")
        field.set("label", t(lang, "admin_wfstep_text_after_upload_form"))
        field.set("type", "memo")
        ret.append(field)

        field = tree.Node("singleobj", "metafield")
        field.set("label", t(lang, "admin_wfstep_single_upload"))
        field.set("type", "check")
        ret.append(field)

        field = tree.Node("limit", "metafield")
        field.set("label", t(lang, "admin_wfstep_uploadtype"))
        field.set("type", "text")
        ret.append(field)

        return ret

