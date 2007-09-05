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

def mkfilelist(node, deletebutton=0, language=None, request=None):
    return request.getTAL("objtypes/workflow.html", {"files":node.getFiles(), "node":node, "delbutton":deletebutton} , macro="workflow_filelist")
    

class WorkflowStep_ShowData(WorkflowStep):

    def show_workflow_node(self, node, req):
        
        if "gotrue" in req.params:
            return self.forwardAndShow(node, True, req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)
        
        key = req.params.get("key", req.session.get("key",""))

        prefix = self.get("prefix")
        suffix = self.get("suffix")

        masks = self.get("masks")
        if not masks:
            masklist = ["editmask"]
        else:
            masklist = masks.split(";")

        fieldmap = []
        for maskname in masklist:
            mask = getMetaType(node.type).getMask(maskname)
            fieldmap += [mask.getViewHTML([node],VIEW_HIDE_EMPTY,language=lang(req))]

        #printlink = ""
        #try:
        #    f = node.show_node_printview()
        #    printlink = """<button onClick="window.open('print?id="""+node.id+"""','printwin')">Daten drucken</button>"""
        #except:
        #    pass

        filelist = ""
        if node.getFiles():
            filelist = mkfilelist(node, request=req)

        return req.getTAL("objtypes/workflow.html", {"key": key, "filelist": filelist, "fields": fieldmap, "prefix": prefix, "suffix": suffix, "buttons": self.tableRowButtons(node)}, macro="workflow_showdata")


    def metaFields(self):
        ret = list()
        field = tree.Node("prefix", "metafield")
        field.set("label", "Text vor den Daten")
        field.set("type", "memo")
        ret.append(field)
        
        field = tree.Node("suffix", "metafield")
        field.set("label", "Text nach den Daten")
        field.set("type", "memo")
        ret.append(field)
        
        field = tree.Node("masks", "metafield")
        field.set("label", "anzuzeigende Masken (;-separiert)")
        field.set("type", "text")
        ret.append(field)
        return ret
