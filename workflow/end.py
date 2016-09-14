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
import logging
from .workflow import WorkflowStep, registerStep
from core.translation import t, addLabels
import core.config as config
from utils.date import now
from schema.schema import Metafield
from core import db

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-end", WorkflowStep_End)
    registerStep("workflowstep_end")
    addLabels(WorkflowStep_End.getLabels())


class WorkflowStep_End(WorkflowStep):

    def show_workflow_node(self, node, req):

        if self.get("endremove") != "":
            # remove obj from workflownode
            self.children.remove(node)

        db.session.commit()
        if self.get("endtext") != "":
            link = u"https://{}/pnode?id={}&key={}".format(config.get("host.name"),
                                                          node.id,
                                                          node.get("key"))
            link2 = u"https://{}/node?id={}".format(config.get("host.name"),
                                                   node.id)

            return req.getTALstr(self.get("endtext"), {"node": node, "link": link, "link2": link2})
        return req.getTALstr(
            '<p><a href="/publish" i18n:translate="workflow_back">TEXT</a></p><h2 i18n:translate="wf_step_ready">Fertig</h2><p>&nbsp;</p><p i18n:translate="workflow_step_ready_msg">Das Objekt <span tal:content="node" i18n:name="name"/> ist am Ende des Workflows angekommen.</p>',
            {
                "node": unicode(
                    node.id)})

    def runAction(self, node, op=""):
        # insert node into searchindex
        try:
            if node.get('updatetime') <= unicode(now()):  # do only if date in the past
                node.set('updatetime', unicode(now()))
            db.session.commit()
        except:
            logg.exception("exception in workflow step end, runAction failed")

    def metaFields(self, lang=None):
        ret = []
        field = Metafield("endtext")
        field.set("label", t(lang, "admin_wfstep_endtext"))
        field.set("type", "memo")
        ret.append(field)

        field = Metafield("endremove")
        field.set("label", t(lang, "admin_wfstep_endremove"))
        field.set("type", "check")
        ret.append(field)
        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-end", "Endknoten"),
                    ("admin_wfstep_endtext", "Textseite"),
                    ("admin_wfstep_endremove", "Entferne aus Workflow"),
                ],
                "en":
                [
                    ("workflowstep-end", "End node"),
                    ("admin_wfstep_endtext", "Text Page"),
                    ("admin_wfstep_endremove", "Remove from Workflow"),
                ]
                }
