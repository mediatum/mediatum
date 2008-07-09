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
from workflow import WorkflowStep
import utils.fileutils as fileutils
from showdata import mkfilelist
from core.translation import t,lang

class WorkflowStep_Upload(WorkflowStep):
   
  
    def show_workflow_node(self, node, req):
        error = ""

        for key in req.params.keys():
            if key.startswith("delete_"):
                filename = key[7:-2]
                for file in node.getFiles():
                    if file.getName() == filename:
                        node.removeFile(file)
            
        if "file" in req.params:
            file = req.params["file"]
            del req.params["file"]
            if hasattr(file,"filename") and file.filename:
                file = fileutils.importFile(file.filename,file.tempname)
                node.addFile(file)
                if hasattr(node,"event_files_changed"):
                    node.event_files_changed()
        
        
        if "gotrue" in req.params:
            if hasattr(node,"event_files_changed"):
                node.event_files_changed()
            if len(node.getFiles())>0:
                return self.forwardAndShow(node, True, req)
            else:
                error = t(req, "no_file_transferred") 

        if "gofalse" in req.params:
            if hasattr(node,"event_files_changed"):
                node.event_files_changed()
            if len(node.getFiles())>0:
                return self.forwardAndShow(node, False, req)
            else:
                error = t(req, "no_file_transferred") 

        filelist = mkfilelist(node, 1, request=req)
        
        prefix = self.get("prefix")
        suffix = self.get("suffix")

        return req.getTAL("workflow/upload.html", {"obj": node.id, "id": self.id,"prefix": prefix, "suffix": suffix, "filelist": filelist, "node": node, "buttons": self.tableRowButtons(node), "error":error}, macro="workflow_upload")

    def metaFields(self, lang=None):
        ret = list()
        field = tree.Node("prefix", "metafield")
        field.set("label", "Text vor dem Upload-Formular")
        field.set("type", "memo")
        ret.append(field)
        
        field = tree.Node("suffix", "metafield")
        field.set("label", "Text nach dem Upload-Formular")
        field.set("type", "memo")
        ret.append(field)
        return ret
