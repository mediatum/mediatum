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
from upload import WorkflowStep #relative import
from schema.schema import getMetaType
from core.translation import t,lang
import utils.date as date
from workflow import mkKey

class WorkflowStep_Start(WorkflowStep):
    def show_workflow_step(self, req):

        typename = self.get("newnodetype")

        if "Erstellen" in req.params:
            if typename not in [ty.strip() for ty in self.get("newnodetype").split(";")]:
                return '<i>' + t(lang(req),"permission_denied") + '</i>'
            node = tree.Node(name="", type=typename)
            self.addChild(node)
            node.setAccess("read", "{user workflow}")
            node.set("creator", "workflow-"+self.getParents()[0].getName())
            node.set("creationtime", date.format_date())
            node.set("key", mkKey())
            req.session["key"] = node.get("key")
            return self.forwardAndShow(node, True, req)
       
        types = []
        for a in typename.split(";"):
            if a:
                m = getMetaType(a)
                # we could now check m.isActive(), but for now let's
                # just take all specified metatypes, so that edit area
                # and workflow are independent on this
                types += [m]

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

        return req.getTAL("workflow/start.html", {"types":types, "id":self.id, "js":js}, macro="workflow_start")
        
    def metaFields(self):
        ret = list()
        field = tree.Node("newnodetype", "metafield")
        field.set("label", "erstellbare Node-Typen (;-separiert)")
        field.set("type", "text")
        ret.append(field)
        return ret
