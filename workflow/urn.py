"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Peter Heckl <heckl@ub.tum.de>

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

import logging
import re

from .workflow import WorkflowStep, registerStep
import utils.urn as utilsurn
from core.translation import t, addLabels
import utils.date as date


logg = logging.getLogger(__name__)


def register():
    tree.registerNodeClass("workflowstep-addurn", WorkflowStep_Urn)
    registerStep("workflowstep-addurn")
    addLabels(WorkflowStep_Urn.getLabels())


class WorkflowStep_Urn(WorkflowStep):

    def show_workflow_node(self, node, req):
        attrname = self.get("attrname")
        niss = self.get("niss")

        if attrname == "":
            attrname = "urn"

        # create urn only for nodes with files
        if len(node.getFiles()) > 0:
            urn = node.get(attrname)
            if urn:
                node.set(attrname, utilsurn.increaseURN(node.get(attrname)))
            else:
                for var in re.findall(r'\[(.+?)\]', niss):
                    if var == "att:id":
                        niss = niss.replace("[" + var + "]", node.id)
                    elif var.startswith("att:"):
                        val = node.get(var[4:])
                        try:
                            val = date.format_date(date.parse_date(val), '%Y%m%d')
                        except:
                            logg.exception("exception in workflow step urn, date formatting failed, ignoring")
                            
                        niss = niss.replace("[" + var + "]", val)
                node.set(attrname, utilsurn.buildNBN(self.get("snid1"), self.get("snid2"), niss))
        return self.forwardAndShow(node, True, req)

    def metaFields(self, lang=None):
        ret = list()
        field = tree.Node("attrname", "metafield")
        field.set("label", t(lang, "admin_wfstep_urn_attrname"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("snid1", "metafield")
        field.set("label", t(lang, "admin_wfstep_urn_snid1"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("snid2", "metafield")
        field.set("label", t(lang, "admin_wfstep_urn_snid2"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("niss", "metafield")
        field.set("label", t(lang, "admin_wfstep_urn_niss"))
        field.set("type", "text")
        ret.append(field)
        return ret

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
