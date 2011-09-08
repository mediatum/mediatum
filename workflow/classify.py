"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Arne Seifert <arne.seifert@tum.de>

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

from upload import WorkflowStep
from core.translation import t
import core.tree as tree


class WorkflowStep_Classify(WorkflowStep):
    """
        workflowstep that add item to selectable nodes.
        nodelist stored in attribute 'destination', ;-separated
    """
    
    def show_workflow_node(self, node, req):
        return self.forwardAndShow(node, True, req)
        
    def runAction(self, node, op=""):
        for nid in self.get('destination').split(";"):
            try:
                tree.getNode(nid).addChild(node)
            except tree.NoSuchNodeError:
                pass

    def metaFields(self, lang=None):
        ret = []
        field = tree.Node("destination", "metafield")
        field.set("label", t(lang, "admin_wfstep_classify_destination"))
        field.set("type", "treeselect")
        ret.append(field)
        return ret
        
    def getLabels(self):
        return { "de":
            [
                ("workflowstep-classify", "Klassifizieren"),
                ("admin_wfstep_classify_destination", "Zielknoten-ID"),
            ],
           "en":
            [
                ("workflowstep-classify", "classify"),
                ("admin_wfstep_classify_destination", "ID of destination node"),
            ]
            }
        