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
from .workflow import WorkflowStep, registerStep
from core import UserGroup, db
from core.permission import get_or_add_access_rule
q = db.query


def register():
    registerStep("workflowstep_publish")


class WorkflowStep_Publish(WorkflowStep):

    def runAction(self, node, op=""):
        ugid = q(UserGroup).filter_by(name=u'_workflow').one().id

        # remove access rule with '_workflow' user group id
        special_access_ruleset = node.get_special_access_ruleset(ruletype=u'read')
        workflow_rule = get_or_add_access_rule(group_ids=[ugid])

        for rule_assoc in special_access_ruleset.rule_assocs:
            if rule_assoc.rule == workflow_rule:
                db.session.delete(rule_assoc)

        db.session.commit()
        self.forward(node, True)
