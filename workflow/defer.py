# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Iryna Feuerstein <feuersti@in.tum.de>

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
import utils.date as date
import core.schedules as schedules
from .workflow import WorkflowStep, registerStep
from core.translation import t, addLabels


logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-defer", WorkflowStep_Defer)
    registerStep("workflowstep-defer")
    addLabels(WorkflowStep_Defer.getLabels())


class WorkflowStep_Defer(WorkflowStep):

    """
    Defer the publication of the object passed by this step til the specified
    date.

    The name of object attributes specifying defer date and actions to be
    suppressed shall be given. They will be saved in nodes attrname and
    accesstype respectively.
    """

    def runAction(self, node, op=""):
        """
        The actual proccessing of the node object takes place here.

        Read out the values of attrname and accesstype if any. Generate the
        ACL-rule, and save it.
        """
        l_date = node.get(self.get('attrname'))
        if l_date:
            if date.validateDateString(l_date):
                try:
                    node.set('updatetime', date.format_date(date.parse_date(l_date)))
                    formated_date = date.format_date(date.parse_date(l_date), "dd.mm.yyyy")
                    for item in self.get('accesstype').split(';'):
                        node.setAccess(item, "{date >= %s}" % formated_date)
                    node.getLocalRead()

                    if self.get('recipient'):  # if the recipient-email was entered, create a scheduler
                        attr_dict = {'single_trigger': l_date, 'function': "test_sendmail01",
                                     'nodelist': list(node.id), 'attr_recipient': self.get('recipient'),
                                     'attr_subject': u"{} ID: {}".format(self.get('subject'),
                                                                         node.id),
                                     'attr_body': self.get('body')}

                        schedules.create_schedule("WorkflowStep_Defer", attr_dict)

                except ValueError:
                    logg.exception("exception in workflow step defer, runAction failed")

    def show_workflow_node(self, node, req):
        return self.forwardAndShow(node, True, req)

    def metaFields(self, lang=None):
        ret = list()
        field = tree.Node("attrname", "metafield")
        field.set("label", t(lang, "attributname"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("accesstype", "metafield")
        field.set("label", t(lang, "accesstype"))
        field.set("type", "mlist")
        field.set("valuelist", ";read;write;data")
        ret.append(field)

        field = tree.Node("recipient", "metafield")
        field.set("label", t(lang, "admin_wfstep_email_recipient"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("subject", "metafield")
        field.set("label", t(lang, "admin_wfstep_email_subject"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("body", "metafield")
        field.set("label", t(lang, "admin_wfstep_email_text"))
        field.set("type", "memo")
        ret.append(field)

        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-defer", u"Freischaltverzögerung"),
                    ("attributname", "Attributname"),
                    ("accesstype", "Zugriffsattribut"),
                ],
                "en":
                [
                    ("workflowstep-defer", "Defer-Field"),
                    ("attributname", "Attributename"),
                    ("accesstype", "Access attribute"),
                ]
                }
