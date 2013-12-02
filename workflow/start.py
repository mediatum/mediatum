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
import core.tree as tree
import core.config as config
from workflow import WorkflowStep, registerStep
from schema.schema import getMetaType
from core.translation import t, lang, addLabels, switch_language
import utils.date as date
from utils.utils import mkKey

def register():
    tree.registerNodeClass("workflowstep-start", WorkflowStep_Start)
    registerStep("workflowstep-start")
    addLabels(WorkflowStep_Start.getLabels())

class WorkflowStep_Start(WorkflowStep):

    def show_workflow_step(self, req):
        typenames = self.get("newnodetype").split(";")
        wfnode = self.getParents()[0]
        redirect = ""
        message = ""
        
        # check existence of metadata types listed in the definition of the start node
        mdts = tree.getRoot("metadatatypes")
        for schema in typenames:
            if not mdts.hasChild(schema.strip().split("/")[-1]):
                return ('<i>%s: %s </i>') % (schema, t(lang(req), "permission_denied"))

        if "workflow_start" in req.params:
            switch_language(req, req.params.get('workflow_language'))
            node = tree.Node(name="", type=req.params.get('selected_schema'))
            self.addChild(node)
            node.setAccess("read", "{user workflow}")
            node.set("creator", "workflow-"+self.getParents()[0].getName())
            node.set("creationtime", date.format_date())
            node.set("system.wflanguage", req.params.get('workflow_language'))
            node.set("key", mkKey())
            node.set("system.key", node.get("key")) # initial key identifier
            req.session["key"] = node.get("key")
            return self.forwardAndShow(node, True, req)
            
        elif "workflow_start_auth" in req.params: # auth node by id and key
            try:
                node = tree.getNode(req.params.get('nodeid'))

                if node.get('system.key')==req.params.get('nodekey') and node.get('key')!=req.params.get('nodekey'): # startkey, but protected
                    message = "workflow_start_err_protected"
                elif node.get('key')==req.params.get('nodekey'):
                    redirect = "/pnode?id=%s&key=%s" %(node.id, node.get('key'))
                else:
                    message = "workflow_start_err_wrongkey"
            except:
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

        js="""
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

        return req.getTAL("workflow/start.html", {'types':types, 'id':self.id, 'js':js, 'starttext':self.get('starttext'), 'languages':self.getParents()[0].getLanguages(), 'currentlang':lang(req), 'sidebartext':self.getSidebarText(lang(req)), 'redirect': redirect, 'message':message, 'allowcontinue':self.get('allowcontinue')}, macro="workflow_start")


    def metaFields(self, lang=None):
        ret = []
        field = tree.Node("newnodetype", "metafield")
        field.set("label", t(lang, "admin_wfstep_node_types_to_create"))
        field.set("type", "text")
        ret.append(field)
        field = tree.Node("starttext", "metafield")
        field.set("label", t(lang, "admin_wfstep_starttext"))
        field.set("type", "htmlmemo")
        ret.append(field)
        field = tree.Node("allowcontinue", "metafield")
        field.set("label", t(lang, "admin_wfstep_allowcontinue"))
        field.set("type", "check")
        ret.append(field)
        return ret
        
    @staticmethod
    def getLabels():
        return { "de":
            [
                ("workflowstep-start", "Startknoten"),
                ("admin_wfstep_starttext", "Text vor Auswahl"),
                ("admin_wfstep_node_types_to_create", "Erstellbare Node-Typen (;-separiert)"),
                ("admin_wfstep_allowcontinue", "Fortsetzen erlauben"),
                ("workflow_start_create", "Erstellen"),
                ("workflow_start_chooselang", "Bitte Sprache w\xc3\xa4hlen / Please choose language"),
                ("workflow_start_type", "Melden Ihrer"),
                ("workflow_start_type_m", "Melden Ihrer / Registering your"),
                ("workflow_start_create_m", "Erstellen / Create"),
                ("workflow_start_continue_header", "Publizieren fortsetzen"),
                ("workflow_start_continue_header_m", "Publizieren fortsetzen / Continue publishing"),
                ("workflow_start_identificator", "Identifikationsnummer"),
                ("workflow_start_identificator_m", "Identifikationsnummer / Identification Number"),
                ("workflow_start_key", "Schl\xc3\xbcssel"),
                ("workflow_start_key_m", "Schl\xc3\xbcssel / Key"),
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
                ("workflow_start_create", "Create / Erstellen"),
                ("workflow_start_chooselang", "Please choose language / Bitte Sprache w\xc3\xa4hlen"),
                ("workflow_start_identificator", "Identification Number"),
                ("workflow_start_key", "Key"),
                ("workflow_start_continue", "Continue / Fortsetzen"),
                ("workflow_start_err_wrongkey", "wrong Identificator/Key."),
                ("workflow_start_err_protected", "no changes needed."),
            ]
        }
