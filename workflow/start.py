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
from workflow import WorkflowStep, registerStep
from schema.schema import getMetaType
from core.translation import t,lang, addLabels
import utils.date as date
from utils.utils import mkKey

def register():
    tree.registerNodeClass("workflowstep-start", WorkflowStep_Start)
    registerStep("workflowstep-start")
    addLabels(getLabels())

class WorkflowStep_Start(WorkflowStep):

    def show_workflow_step(self, req):
        typenames = self.get("newnodetype").split(";")
        
        # check existence of metadata types listed in the definition of the start node
        mdts = tree.getRoot("metadatatypes")
        for schema in typenames:
            if not mdts.hasChild(schema.strip().split("/")[-1]):
                return ('<i>' + t(lang(req),"permission_denied") + ': %s </i>') % schema

        if "Erstellen" in req.params:
            node = tree.Node(name="", type=req.params.get("selected_schema"))
            self.addChild(node)
            node.setAccess("read", "{user workflow}")
            node.set("creator", "workflow-"+self.getParents()[0].getName())
            node.set("creationtime", date.format_date())
            node.set("key", mkKey())
            req.session["key"] = node.get("key")
            return self.forwardAndShow(node, True, req)
       
        types = []
        for a in typenames:
            if a:
                m = getMetaType(a)
                # we could now check m.isActive(), but for now let's
                # just take all specified metatypes, so that edit area
                # and workflow are independent on this
                types += [(m, a)]
        cookie_error = t(lang(req),"Your browser doesn't support cookies")

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

        return req.getTAL("workflow/start.html", {"types":types, "id":self.id, "js":js, "starttext":self.get('starttext')}, macro="workflow_start")
        
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
        return ret
    
def getLabels(key=None, lang=None):
    return { "de":
        [
            ("workflowstep-start", "Startknoten"),
            ("admin_wfstep_starttext", "Text vor Auswahl"),
            ("admin_wfstep_node_types_to_create", "Erstellbare Node-Typen (;-separiert)"),
        ],
       "en":
        [
            ("workflowstep-start", "Start node"),
            ("admin_wfstep_starttext", "Text in front of selection"),
            ("admin_wfstep_node_types_to_create", "Node types to create (;-separated schema list)"),
        ]
        }
