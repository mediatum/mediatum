# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import re

import mediatumtal.tal as _tal

from .workflow import WorkflowStep, registerStep
import utils.urn as utilsurn
from core.translation import addLabels
import utils.date as date
from core import db
from schema.schema import Metafield

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-addurn", WorkflowStep_Urn)
    registerStep("workflowstep_urn")
    addLabels(WorkflowStep_Urn.getLabels())


class WorkflowStep_Urn(WorkflowStep):

    default_settings = dict(
        attrname="urn",
        snid1="",
        snid2="",
        niss="",
    )

    def show_workflow_node(self, node, req):
        attrname = self.settings["attrname"]
        niss = self.settings["niss"]

        # create urn only for nodes with files
        if len(node.files) > 0:
            urn = node.get(attrname)
            if urn:
                node.set(attrname, utilsurn.increaseURN(node.get(attrname)))
            else:
                for var in re.findall(r'\[(.+?)\]', niss):
                    if var == "att:id":
                        niss = niss.replace("[" + var + "]", unicode(node.id))
                    elif var.startswith("att:"):
                        val = node.get(var[4:])
                        try:
                            val = date.format_date(date.parse_date(val), '%Y%m%d')
                        except:
                            logg.exception("exception in workflow step urn, date formatting failed, ignoring")
                            
                        niss = niss.replace("[" + var + "]", val)
                node.set(attrname, utilsurn.buildNBN(self.settings["snid1"], self.settings["snid2"], niss))
        db.session.commit()
        return self.forwardAndShow(node, True, req)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/urn.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert frozenset(data) == frozenset(("attrname", "snid1", "snid2", "niss"))
        self.settings = data
        db.session.commit()

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-urn", "URN Knoten"),
                    ("admin_wfstep_urn", "URN"),
                    ("admin_wfstep_urn_snid1", "URN SNID 1"),
                    ("admin_wfstep_urn_snid2", "URN SNID 2"),
                    ("admin_wfstep_urn_niss", "URN NISS"),
                    ("admin_wfstep_urn_attrname", "URN Attributname"),

                ],
                "en":
                [
                    ("workflowstep-condition", "URN node"),
                    ("admin_wfstep_condition", "URN"),
                    ("admin_wfstep_urn_snid1", "URN SNID 1"),
                    ("admin_wfstep_urn_snid2", "URN SNID 2"),
                    ("admin_wfstep_urn_niss", "URN NISS"),
                    ("admin_wfstep_urn_attrname", "URN attribute name"),

                ]
                }
