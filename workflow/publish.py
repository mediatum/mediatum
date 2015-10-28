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
from core import db
from core.database.postgres.permission import AccessRule
from core import UserGroup
q = db.query


def register():
    #tree.registerNodeClass("workflowstep-publish", WorkflowStep_Publish)
    registerStep("workflowstep_publish")


class WorkflowStep_Publish(WorkflowStep):

    def runAction(self, node, op=""):

        ugid = q(UserGroup).filter_by(name=u'Workflow').one().id

        # remove access rule with 'Workflow' user group id
        for e in node.access_rule_assocs.filter_by(ruletype=u'read'):
            ar = q(AccessRule).get(e.rule_id)
            if ar and ar.group_ids and (ugid in ar.group_ids):
                node.access_rule_assocs.filter_by(rule_id=ar.id).delete()
                db.session.delete(ar)

        db.session.commit()

        self.forward(node, True)
