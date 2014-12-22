"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Werner Neudenberger <neudenberger@ub.tum.de>


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
import core.tree as tree
import core.users as users
import core.config as config
from .workflow import WorkflowStep, getNodeWorkflow, getNodeWorkflowStep, registerStep
from core.translation import t, lang, addLabels
from utils.date import format_date

LDAP_AVAILABLE = True
LDAP_MODULE_PRESENT = True
DEFAULT_ATTRIBUTE_FOR_USERNAME = "system.ldapauth_username"

try:
    import ldap
except:
    LDAP_MODULE_PRESENT = False

if LDAP_MODULE_PRESENT and config.get("ldap.activate", "").lower() == "true":
    from core.userldap import LDAPUser
else:
    LDAP_AVAILABLE = False


logg = logging.getLogger(__name__)


def register():
    tree.registerNodeClass("workflowstep-ldapauth", WorkflowStep_LdapAuth)
    registerStep("workflowstep-ldapauth")
    addLabels(WorkflowStep_LdapAuth.getLabels())


class WorkflowStep_LdapAuth(WorkflowStep):

    def show_workflow_node(self, node, req, data=None):
        if "gotrue" in req.params:

            if not LDAP_AVAILABLE:
                del req.params['gotrue']
                return self.show_workflow_node(node, req)

            current_workflow = getNodeWorkflow(node)
            username = req.params.get("username", "")
            password = req.params.get("password", "")

            if not (username and password):
                req.params["ldapauth_error"] = "%s: %s" % (
                    format_date().replace('T', ' - '), t(lang(req), "admin_wfstep_ldapauth_empty_entry"))
                del req.params['gotrue']
                return self.show_workflow_node(node, req)

            logg.info("workflow '%s', node %s: going to authenticate username '%s' via ldap", current_workflow.name, node.id, username)

            ldap_user = LDAPUser()
            res_dict = ldap_user.authenticate_login(username, password, create_new_user=0)

            if res_dict:
                user_identifier = res_dict.get('dn', '')

                # save user_identifier in node attribute
                attr_name = self.get("attribute_for_user_identifier").strip()
                if not attr_name:
                    attr_name = DEFAULT_ATTRIBUTE_FOR_USERNAME

                node.set(attr_name, user_identifier)
                logg.info("workflow '%s', node %s: success authenticating username '%s': identified as '%s'",
                    current_workflow.name, node.id, username, user_identifier)
                return self.forwardAndShow(node, True, req)

            else:
                logg.info("workflow '%s', node %s: fail authenticating username '%s'", current_workflow.name, node.id, username)
                error = "%s: %s" % (format_date().replace('T', ' - '), t(lang(req), "admin_wfstep_ldapauth_wrong_credentials"))
                current_workflow_step = getNodeWorkflowStep(node)

                # if no 'False' operation for this step is defined, call this step again
                if not current_workflow_step.getFalseId().strip():
                    req.params["ldapauth_error"] = error
                    del req.params['gotrue']
                    return self.show_workflow_node(node, req)

                # forward to 'False' operation, adding ldapauth_error to req.params dict
                return self.forwardAndShow(node, False, req, data={"ldapauth_error": error})

        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        context = {"key": req.params.get("key", req.session.get("key", "")),
                   "user": users.getUserFromRequest(req),
                   "prefix": self.get("prefix"),
                   "buttons": self.tableRowButtons(node)}

        if LDAP_AVAILABLE:
            context['error'] = req.params.get('ldapauth_error', "")
        else:
            context['error'] = t(lang(req), "xadmin_wfstep_ldapauth_no_ldap")

        return req.getTAL("workflow/ldapauth.html", context, macro="workflow_ldapauth")

    def metaFields(self, lang=None):
        if not LDAP_AVAILABLE:
            field = tree.Node("infotext", "metafield")
            field.set("label", t(lang, "xadmin_wfstep_ldapauth_label"))
            field.set("type", "label")
            field.set("value", '<span style="color:#ff0000">' + t(lang, "xadmin_wfstep_ldapauth_text") + '</span>')
            return [field]

        ret = list()
        field = tree.Node("prefix", "metafield")
        field.set("label", t(lang, "admin_wfstep_text_before_data"))
        field.set("type", "memo")
        ret.append(field)

        field = tree.Node("attribute_for_user_identifier", "metafield")
        field.set("label", t(lang, "admin_wfstep_ldapauth_attribute_for_user_identifier"))
        field.set("type", "text")
        ret.append(field)
        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-ldapauth", 'LdapAuth'),

                    ("xadmin_wfstep_ldapauth_label", 'WARNUNG'),
                    ("xadmin_wfstep_ldapauth_text",
                     'Dieser Workflow-Step ist nicht funktional, ldap-Modul oder Konfiguration nicht vorhanden'),
                    ("xadmin_wfstep_ldapauth_no_ldap",
                     'Dieser Schritt ist nicht funktional, da das ldap-Modul oder die Konfiguration fehlen.'),
                ],
                "en":
                [
                    ("workflowstep-ldapauth", 'LdapAuth'),

                    ("xadmin_wfstep_ldapauth_label", 'WARNING'),
                    ("xadmin_wfstep_ldapauth_text", 'this workflow step is not functional, ldap module or configuration missing'),
                    ("xadmin_wfstep_ldapauth_no_ldap", 'this workflow step is not functional, ldap module or configuration missing.'),
                ]
                }
