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
from utils.utils import isNumeric
import core.tree as tree


class WorkflowStep_Classify(WorkflowStep):
    """
        workflowstep that adds item to selectable nodes.
        attributes:
            - destination: list of node ids ;-separated
            - [destination_attr]: attribute name for destination folder
                |substring:start,end for substing of of attribute value
                e.g. 'year|substring:0,4' only year part of date
            - [only_sub]: 0|1 node will only be stored in the subnode
    """
    
    def show_workflow_node(self, node, req):
        return self.forwardAndShow(node, True, req)
        
    def runAction(self, node, op=""):
        name = ""
        func = start = end = None
        attr = self.get('destination_attr')
        if attr!="" and "|" in attr:
            attr, func = attr.split("|")
            
        if attr!="": # name of subnode
            name = node.get(attr)
        if func and func.startswith('substring'): # check for function
            start, end = func[10:].split(",")
        if end and isNumeric(end):
            name = name[:int(end)]
        if start and isNumeric(start):
            name = name[int(start):]

        for nid in self.get('destination').split(";"):
            try:
                pnode = tree.getNode(nid)
                cnode = None
                if name!="":
                    try:
                        cnode = pnode.getChild(name)
                    except tree.NoSuchNodeError:
                        cnode = tree.Node(name, type="directory")
                        pnode.addChild(cnode)
               
                if cnode: # add node to child given by attributename
                    cnode.addChild(node)
                if self.get('only_sub')!='1': # add to node (no hierarchy)
                    pnode.addChild(node)
            except tree.NoSuchNodeError:
                pass

    def metaFields(self, lang=None):
        ret = []
        field = tree.Node("destination", "metafield")
        field.set("label", t(lang, "admin_wfstep_classify_destination"))
        field.set("type", "treeselect")
        ret.append(field)
        field = tree.Node("destination_attr", "metafield")
        field.set("label", t(lang, "admin_wfstep_classify_destination_attr"))
        field.set("type", "text")
        ret.append(field)
        field = tree.Node("only_sub", "metafield")
        field.set("label", t(lang, "admin_wfstep_classify_only_sub"))
        field.set("type", "check")
        ret.append(field)
        return ret
        
    def getLabels(self):
        return { "de":
            [
                ("workflowstep-classify", "Klassifizieren"),
                ("admin_wfstep_classify_destination", "Zielknoten-ID"),
                ("admin_wfstep_classify_destination_attr", "Unterknoten Attribut"),
                ("admin_wfstep_classify_only_sub", "Nur Unterknoten"),
            ],
           "en":
            [
                ("workflowstep-classify", "classify"),
                ("admin_wfstep_classify_destination", "ID of destination node"),
                ("admin_wfstep_classify_destination_attr", "attribute name"),
                ("admin_wfstep_classify_only_sub", "only subnode"),
            ]
            }
        