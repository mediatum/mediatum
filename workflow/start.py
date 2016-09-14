# -*- coding: utf-8 -*-
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
import core.config as config
from .workflow import WorkflowStep, registerStep
from schema.schema import getMetaType
from core.translation import t, lang, addLabels, switch_language
import utils.date as date
from utils.utils import mkKey
from core.systemtypes import Metadatatypes
from core import Node
from core import db
from schema.schema import Metafield
from core.database.postgres.permission import AccessRule, AccessRulesetToRule
from core import UserGroup
from core.permission import get_or_add_access_rule

q = db.query

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-start", WorkflowStep_Start)
    registerStep("workflowstep_start")
    addLabels(WorkflowStep_Start.getLabels())


class WorkflowStep_Start(WorkflowStep):

    def show_workflow_step(self, req):
        typenames = self.get("newnodetype").split(";")
        wfnode = self.parents[0]
        redirect = ""
        message = ""

        # check existence of metadata types listed in the definition of the start node
        mdts = q(Metadatatypes).one()
        for schema in typenames:
            if not mdts.children.filter_by(name=schema.strip().split("/")[-1]).scalar():
                return ('<i>%s: %s </i>') % (schema, t(lang(req), "permission_denied"))

        if "workflow_start" in req.params:
            switch_language(req, req.params.get('workflow_language'))
            content_class = Node.get_class_for_typestring(req.params.get('selected_schema').split('/')[0])
            node = content_class(name=u'', schema=req.params.get('selected_schema').split('/')[1])
            self.children.append(node)

            # create user group named '_workflow' if it doesn't exist
            workflow_group = q(UserGroup).filter_by(name=u'_workflow').scalar()
            if workflow_group is None:
                workflow_group = UserGroup(name=u'_workflow', description=u'internal dummy group for nodes in workflows')
                db.session.add(workflow_group)

            # create access rule with '_workflow' user group
            workflow_rule = get_or_add_access_rule(group_ids=[workflow_group.id])

            special_access_ruleset = node.get_or_add_special_access_ruleset(ruletype=u'read')
            special_access_ruleset.rule_assocs.append(AccessRulesetToRule(rule=workflow_rule))

            node.set("creator", "workflow-" + self.parents[0].name)
            node.set("creationtime", date.format_date())
            node.set("system.wflanguage", req.params.get('workflow_language', req.Cookies.get('language')))
            node.set("key", mkKey())
            node.set("system.key", node.get("key"))  # initial key identifier
            req.session["key"] = node.get("key")
            db.session.commit()
            return self.forwardAndShow(node, True, req)

        elif "workflow_start_auth" in req.params:  # auth node by id and key
            try:
                node = q(Node).get(req.params.get('nodeid'))

                # startkey, but protected
                if node.get('system.key') == req.params.get('nodekey') and node.get('key') != req.params.get('nodekey'):
                    message = "workflow_start_err_protected"
                elif node.get('key') == req.params.get('nodekey'):
                    redirect = "/pnode?id=%s&key=%s" % (node.id, node.get('key'))
                else:
                    message = "workflow_start_err_wrongkey"
            except:
                logg.exception("exception in workflow step start (workflow_start_auth)")
                message = "workflow_start_err_wrongkey"

        types = []
        for a in typenames:
            if a:
                m = getMetaType(a)
                # we could now check m.isActive(), but for now let's
                # just take all specified metatypes, so that edit area
                # and workflow are independent on this
                types += [(m, a)]
        cookie_error = t(lang(req), "Your browser doesn't support cookies")

        js = """
        <script language="javascript">
        function cookie_test() {
            if (document.cookie=="")
                document.cookie = "CookieTest=Erfolgreich";
            if (document.cookie=="") {
                alert("%s");
            }
        }
        cookie_test();
        </script>""" % cookie_error

        return req.getTAL("workflow/start.html",
                          {'types': types,
                           'id': self.id,
                           'js': js,
                           'starttext': self.get('starttext'),
                           'languages': self.parents[0].getLanguages(),
                           'currentlang': lang(req),
                              'sidebartext': self.getSidebarText(lang(req)),
                              'redirect': redirect,
                              'message': message,
                              'allowcontinue': self.get('allowcontinue')},
                          macro="workflow_start")

    def metaFields(self, lang=None):
        ret = []
        field = Metafield("newnodetype")
        field.set("label", t(lang, "admin_wfstep_node_types_to_create"))
        field.set("type", "text")
        ret.append(field)
        field = Metafield("starttext")
        field.set("label", t(lang, "admin_wfstep_starttext"))
        field.set("type", "htmlmemo")
        ret.append(field)
        field = Metafield("allowcontinue")
        field.set("label", t(lang, "admin_wfstep_allowcontinue"))
        field.set("type", "check")
        ret.append(field)
        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-start", "Startknoten"),
                    ("admin_wfstep_starttext", "Text vor Auswahl"),
                    ("admin_wfstep_node_types_to_create", "Erstellbare Node-Typen (;-separiert)"),
                    ("admin_wfstep_allowcontinue", "Fortsetzen erlauben"),
                    ("workflow_start_create", "Erstellen"),
                    ("workflow_start_create_m", "Erstellen / Create"),
                    ("workflow_start_chooselang", u"Bitte Sprache wählen / Please choose language"),
                    ("workflow_start_type", "Melden Ihrer"),
                    ("workflow_start_type_m", "Melden Ihrer / Registering your"),
                    ("workflow_start_continue_header", "Publizieren fortsetzen"),
                    ("workflow_start_continue_header_m", "Publizieren fortsetzen / Continue publishing"),
                    ("workflow_start_identificator", "Identifikationsnummer"),
                    ("workflow_start_identificator_m", "Identifikationsnummer / Identification Number"),
                    ("workflow_start_key", u"Schlüssel"),
                    ("workflow_start_key_m", u"Schlüssel / Key"),
                    ("workflow_start_continue", "Fortsetzen"),
                    ("workflow_start_continue_m", "Fortsetzen / Continue"),
                    ("workflow_start_err_wrongkey", "Fehler bei der Eingabe."),
                    ("workflow_start_err_protected", "Keine Bearbeitung erforderlich."),
                ],
                "en":
                [
                    ("workflowstep-start", "Start node"),
                    ("admin_wfstep_starttext", "Text in front of selection"),
                    ("admin_wfstep_node_types_to_create", "Node types to create (;-separated schema list)"),
                    ("admin_wfstep_allowcontinue", "Allow continue"),
                    ("workflow_start_create", "Create"),
                    ("workflow_start_create_m", "Create / Erstellen"),
                    ("workflow_start_chooselang", u"Please choose language / Bitte Sprache wählen"),
                    ("workflow_start_type", "Registering your"),
                    ("workflow_start_type_m", "Registering your / Melden ihrer"),
                    ("workflow_start_continue_header", "Publizieren fortsetzen"),
                    ("workflow_start_continue_header_m", "Continue publishing / Publizieren fortsetzen "),
                    ("workflow_start_identificator", "Identification Number"),
                    ("workflow_start_identificator_m", "Identification Number / Identifikationsnummer"),
                    ("workflow_start_key", "Key"),
                    ("workflow_start_key_m", u"Key / Schlüssel"),
                    ("workflow_start_continue", "Continue"),
                    ("workflow_start_continue_m", "Continue / Fortsetzen"),
                    ("workflow_start_err_wrongkey", "wrong Identificator/Key."),
                    ("workflow_start_err_protected", "no changes needed."),
                ]
                }
