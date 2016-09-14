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
from .workflow import WorkflowStep, registerStep
from core.translation import t, addLabels
from core import db
from schema.schema import Metafield
from core.database.postgres.permission import AccessRulesetToRule
from psycopg2.extras import DateRange
import datetime
from core.permission import get_or_add_access_rule

q = db.query

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-defer", WorkflowStep_Defer)
    registerStep("workflowstep_defer")
    addLabels(WorkflowStep_Defer.getLabels())


def get_or_add_defer_daterange_rule(year, month, day):
    """Gets an access rule that blocks access until the date given by `year`, `month` and `day`.
    The rule is created if it's missing."""
    dateranges = set([DateRange(datetime.date(year, month, day), datetime.date(9999, 12, 31), '[)')])
    rule = get_or_add_access_rule(dateranges=dateranges)
    return rule


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
                    d = formated_date.split('.')
                    rule = get_or_add_defer_daterange_rule(int(d[2]), int(d[1]), int(d[0]))

                    for access_type in self.get('accesstype').split(';'):
                        special_access_ruleset = node.get_or_add_special_access_ruleset(ruletype=access_type)
                        special_access_ruleset.rule_assocs.append(AccessRulesetToRule(rule=rule))

                    db.session.commit()

                except ValueError:
                    logg.exception("exception in workflow step defer, runAction failed")

    def show_workflow_node(self, node, req):
        return self.forwardAndShow(node, True, req)

    def metaFields(self, lang=None):
        ret = list()
        field = Metafield("attrname")
        field.set("label", t(lang, "attributname"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("accesstype")
        field.set("label", t(lang, "accesstype"))
        field.set("type", "mlist")
        field.set("valuelist", ";read;write;data")
        ret.append(field)

        field = Metafield("recipient")
        field.set("label", t(lang, "admin_wfstep_email_recipient"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("subject")
        field.set("label", t(lang, "admin_wfstep_email_subject"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("body")
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
