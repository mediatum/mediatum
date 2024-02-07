# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal as _tal

from .upload import WorkflowStep
from .workflow import registerStep
from utils.utils import isNumeric
from core.database.postgres.node import Node
from core import db
from contenttypes.container import Directory

q = db.query


def register():
    registerStep("workflowstep_classify")


class WorkflowStep_Classify(WorkflowStep):

    """
        workflowstep that adds item to selectable nodes.
        attributes:
            - destination: list of node ids line-separated
            - [destination_attr]: attribute name for destination folder
                |substring:start,end for substing of of attribute value
                e.g. 'year|substring:0,4' only year part of date
            - [only_sub]: 0|1 node will only be stored in the subnode
    """

    default_settings = dict(
        destination=(),
        destination_attr="",
        only_sub=False,
    )

    def show_workflow_node(self, node, req):
        return self.forwardAndShow(node, True, req)

    def runAction(self, node, op=""):
        name = ""
        func = start = end = None
        attr = self.settings['destination_attr']
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

        for nid in self.settings['destination']:
            pnode = q(Node).get(nid)
            if pnode:
                if name != "":
                    cnode = pnode.children.filter_by(name=name).scalar()
                    if cnode is None:
                        cnode = Directory(name)
                        pnode.children.append(cnode)
                    cnode.children.append(node)
                if not self.settings['only_sub']:  # add to node (no hierarchy)
                    pnode.children.append(node)
                db.session.commit()

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/classify.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        data["only_sub"] = bool(data.get("only_sub"))
        data["destination"] = filter(None, (s.strip() for s in data["destination"].split("\r\n")))
        assert frozenset(data) == frozenset(("destination", "destination_attr", "only_sub"))
        self.settings = data
        db.session.commit()
