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

from .upload import WorkflowStep
from .workflow import registerStep
from core.translation import t, addLabels
from utils.utils import isNumeric
from core import Node
from core import db
from schema.schema import Metafield

q = db.query


def register():
    #tree.registerNodeClass("workflowstep-classify", WorkflowStep_Classify)
    # registerStep("workflowstep-classify")
    registerStep("workflowstep_classify")
    addLabels(WorkflowStep_Classify.getLabels())


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
        if attr != "" and "|" in attr:
            attr, func = attr.split("|")

        if attr != "":  # name of subnode
            name = node.get(attr)
        if func and func.startswith('substring'):  # check for function
            start, end = func[10:].split(",")
        if end and isNumeric(end):
            name = name[:int(end)]
        if start and isNumeric(start):
            name = name[int(start):]

        for nid in self.get('destination').split(";"):
            pnode = q(Node).get(nid)
            cnode = None
            if pnode:
                if name != "":
                    cnode = pnode.children.filter_by(name=name).scalar()
                    if cnode is None:
                        cnode = Node(name, type="directory")
                        pnode.children.append(cnode)

                if cnode:  # add node to child given by attributename
                    cnode.children.append(node)
                if self.get('only_sub') != '1':  # add to node (no hierarchy)
                    pnode.children.append(node)
                db.session.commit()

    def metaFields(self, lang=None):
        ret = []
        field = Metafield("destination")
        field.set("label", t(lang, "admin_wfstep_classify_destination"))
        field.set("type", "treeselect")
        ret.append(field)
        field = Metafield("destination_attr")
        field.set("label", t(lang, "admin_wfstep_classify_destination_attr"))
        field.set("type", "text")
        ret.append(field)
        field = Metafield("only_sub")
        field.set("label", t(lang, "admin_wfstep_classify_only_sub"))
        field.set("type", "check")
        ret.append(field)
        # db.session.commit()
        return ret

    @staticmethod
    def getLabels():
        return {"de":
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
