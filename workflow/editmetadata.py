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
from workflow import WorkflowStep
import core.tree as tree
from core.translation import t,lang
from schema.schema import getMetaType

class WorkflowStep_EditMetadata(WorkflowStep):
    def show_workflow_node(self, node, req):
        result = ""
        error = ""
        key = req.params.get("key", req.session.get("key",""))

        maskname = self.get("mask")
        mask = getMetaType(node.type).getMask(maskname)

        if "metaDataEditor" in req.params:
            mask.updateNode([node], req)
            missing = mask.validate([node])
            print "datum:",  mask.validate([node])
            if not missing or "gofalse" in req.params:
                op = "gotrue" in req.params
                return self.forwardAndShow(node, op, req)
            else:
                error = '<p class="error">'+ t(lang(req),"workflow_error_msg")+'</p>'
                req.params["errorlist"] = missing
        
        return req.getTAL("workflow/editmetadata.html", {"name":self.getName(), "error":error, "key":key, "mask":mask.getFormHTML([node],req), "buttons":self.tableRowButtons(node)}, macro="workflow_metadateneditor")
    
    def metaFields(self, lang=None):
        ret = list()
        field = tree.Node("mask", "metafield")
        field.set("label", "Editor-Maske")
        field.set("type", "text")
        ret.append(field)
        return ret
