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

class WorkflowStep_TextPage(WorkflowStep):
    def show_workflow_node(self, node, req):
        if "gotrue" in req.params:
            return self.forwardAndShow(node, True, req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        text = self.get("text")
        
        return req.getTALstr(""" 
                <tal:block tal:replace="raw python:text"/>
                <table>
                <tal:block tal:replace="raw python:buttons"/>
                </table>
                """, {"text":text, "buttons": self.tableRowButtons(node)})
    
    def metaFields(self):
        ret = list()
        field = tree.Node("text", "metafield")
        field.set("label", "anzuzeigender Text")
        field.set("type", "memo")
        ret.append(field)
        return ret
