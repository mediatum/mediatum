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
from workflow import WorkflowStep,getNodeWorkflow,getNodeWorkflowStep
from core.translation import t,lang
from core.userldap import LDAPUser
from utils.date import format_date

DEFAULT_ATTRIBUTE_FOR_USERNAME = "system.ldapauth_username"

class WorkflowStep_LdapAuth(WorkflowStep):

    def show_workflow_node(self, node, req, data=None):
        if "gotrue" in req.params:
            current_workflow = getNodeWorkflow(node)
            username = req.params.get("username", "")
            password = req.params.get("password", "")
            
            if not (username and password):
                req.params["ldapauth_error"] = "%s: %s" % (format_date().replace('T',' - '), t(lang(req), "admin_wfstep_ldapauth_empty_entry"))
                del req.params['gotrue']
                return self.show_workflow_node(node, req)

            logging.getLogger("workflows").info("workflow '%s', node %s: going to authenticate username '%s' via ldap ..." %(current_workflow.name, node.id, username))
            
            ldap_user = LDAPUser()
            res_dict = ldap_user.authenticate_login(username, password, create_new_user=0)
 
            if res_dict:
                user_identifier = res_dict.get('dn', '')
                
                # save user_identifier in node attribute
                attr_name = self.get("attribute_for_user_identifier").strip()
                if not attr_name:
                    attr_name = DEFAULT_ATTRIBUTE_FOR_USERNAME 
                    
                node.set(attr_name, user_identifier)
                logging.getLogger("workflows").info("workflow '%s', node %s: success authenticating username '%s': identified as '%s'" % (current_workflow.name, node.id, username, user_identifier)) 
                return self.forwardAndShow(node, True, req)
                
            else:
                logging.getLogger("workflows").info("workflow '%s', node %s: fail authenticating username '%s'" % (current_workflow.name, node.id, username))
                error = "%s: %s" % (format_date().replace('T',' - '), t(lang(req), "admin_wfstep_ldapauth_wrong_credentials"))
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

        context = {"key": req.params.get("key", req.session.get("key","")),
                   "error": req.params.get('ldapauth_error', ''),
                   "user": users.getUserFromRequest(req),
                   "prefix": self.get("prefix"),
                   "buttons": self.tableRowButtons(node)}
                   
        return req.getTAL("workflow/ldapauth.html", context, macro="workflow_ldapauth")
            
    def metaFields(self, lang=None):
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
