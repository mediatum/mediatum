# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal as _tal

from .upload import WorkflowStep
from .workflow import registerStep
from core.translation import addLabels
from utils.utils import isNumeric
from core import Node
from core import db
from schema.schema import Metafield
from contenttypes.container import Directory

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
            if nid:
                pnode = q(Node).get(nid)
                cnode = None
                if pnode:
                    if name != "":
                        cnode = pnode.children.filter_by(name=name).scalar()
                        if cnode is None:
                            cnode = Directory(name)
                            pnode.children.append(cnode)

                    if cnode:  # add node to child given by attributename
                        cnode.children.append(node)
                    if self.get('only_sub') != '1':  # add to node (no hierarchy)
                        pnode.children.append(node)
                    db.session.commit()

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            dict(
                destination=self.get('destination'),
                destination_attr=self.get('destination_attr'),
                only_sub=self.get('only_sub'),
            ),
            file="workflow/classify.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        for attr in ('destination', 'destination_attr'):
            self.set(attr, data.pop(attr))
        self.set('only_sub', "1" if data.pop('only_sub', None) else "")
        assert not data
        db.session.commit()

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-classify", "Klassifizieren"),
                    ("admin_wfstep_classify_destination", "Zielknoten-IDs ;-getrennt"),
                    ("admin_wfstep_classify_destination_attr", "Unterknoten Attribut"),
                    ("admin_wfstep_classify_only_sub", "Nur Unterknoten"),
                ],
                "en":
                [
                    ("workflowstep-classify", "classify"),
                    ("admin_wfstep_classify_destination", "IDs of destination node ;-separated"),
                    ("admin_wfstep_classify_destination_attr", "attribute name"),
                    ("admin_wfstep_classify_only_sub", "only subnode"),
                ]
                }
