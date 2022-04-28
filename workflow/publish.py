# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from .workflow import WorkflowStep, registerStep
from core.translation import t, addLabels
from core import UserGroup, db
from core.permission import get_all_access_rules
from core.users import user_from_session as _user_from_session
from utils.date import now
from schema.schema import Metafield
import logging

q = db.query
logg = logging.getLogger(__name__)


def register():
    registerStep("workflowstep_publish")
    addLabels(WorkflowStep_Publish.getLabels())


class WorkflowStep_Publish(WorkflowStep):

    def runAction(self, node, op=""):
        ugid = q(UserGroup).filter_by(name=u'_workflow').one().id
        user = _user_from_session()

        # remove access rule with '_workflow' user group id
        # XXX the following debug messages are needed for analyzing the problem that
        # XXX some dissertations are not published which means that the special_access_ruleset
        # XXX is not removed
        logg.debug("publish node id = %d: get_special_access_ruleset", node.id)
        special_access_ruleset = node.get_special_access_ruleset(ruletype=u'read')
        workflow_rules = get_all_access_rules(group_ids=[ugid])

        logg.debug("publish node id = %d: loop over special_access_ruleset.rule_assocs", node.id)

        for rule_assoc in special_access_ruleset.rule_assocs:
            logg.debug("publish node id = %d: rule_id = %d ruleset_name = '%s'",
                       node.id, rule_assoc.rule_id, rule_assoc.ruleset_name)
            for workflow_rule in workflow_rules:
                if rule_assoc.rule == workflow_rule:
                    logg.debug("publish node id = %d: delete rule_id = %d ruleset_name = '%s'",
                               node.id, rule_assoc.rule_id, rule_assoc.ruleset_name)
                    db.session.delete(rule_assoc)
                    break

        db.session.commit()

        # set updatetime (possibly publish tag),
        # but refrain from doing so if updatetime is
        # in the future (this indicates an embargo)
        if node.get('updatetime') <= unicode(now()):
            if self.get("publishsetpublishedversion") != "":
                # set publish tag
                with node.new_tagged_version(publish='published', user=user):
                    node.set_legacy_update_attributes(user) # note: also updatetime is set
            elif self.get("publishsetupdatetime") != "":
                node.set('updatetime', unicode(now()))
                db.session.commit()
        logg.debug("publish node id = %d: db.session.commit()", node.id)

        self.forward(node, True)

    def metaFields(self, lang=None):
        ret = list()
        field = Metafield("publishsetpublishedversion")
        field.set("label", t(lang, "admin_wfstep_publishsetpublishedversion"))
        field.set("type", "check")
        ret.append(field)

        field = Metafield("publishsetupdatetime")
        field.set("label", t(lang, "admin_wfstep_publishsetupdatetime"))
        field.set("type", "check")
        ret.append(field)
        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("admin_wfstep_publishsetpublishedversion", "Setze Publizierte Version"),
                    ("admin_wfstep_publishsetupdatetime", "Setze Aktualisierungszeit"),
                ],
                "en":
                [
                    ("admin_wfstep_publishsetpublishedversion", "set published version"),
                    ("admin_wfstep_publishsetupdatetime", "set updatetime"),
                ]
                }
