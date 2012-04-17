"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Iryna Feuerstein <feuersti@in.tum.de>

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
import utils.date as date
from workflow import WorkflowStep
from core.translation import t

class WorkflowStep_Defer(WorkflowStep):
    """
    Defer the publication of the object passed by this step til the specified 
    date.
    
    The name of object attributes specifying defer date and actions to be 
    suppressed shall be given. They will be saved in nodes attrname and 
    accesstype respectively.
    """

    def runAction(self, node, op=""):
        """
        The actual proccessing of the node object takes place here.
        
        Read out the values of attrname and accesstype if any. Generate the
        ACL-rule, and save it.
        """
        l_date = node.get(self.get('attrname'))
        if l_date:
            if date.validateDateString(l_date):
                try:
                    node.set('updatetime', date.format_date(date.parse_date(l_date)))
                    l_date = date.format_date(date.parse_date(l_date), "dd.mm.yyyy")
                    for item in self.get('accesstype').split(';'):
                        node.setAccess(item, "{date >= %s}" % l_date)
                    node.getLocalRead()
                except ValueError, e:
                    print "Error: %s" % e

    def show_workflow_node(self, node, req):
        return self.forwardAndShow(node, True, req)
        
    def metaFields(self, lang=None):
        ret = list()
        field = tree.Node("attrname", "metafield")
        field.set("label", t(lang, "attributname"))
        field.set("type", "text")
        ret.append(field)
        
        field = tree.Node("accesstype", "metafield")
        field.set("label", t(lang, "accesstype"))
        field.set("type", "mlist")
        field.set("valuelist", ";read;write;data")
        ret.append(field)
        return ret
        
    def getLabels(self):
        return { "de":
            [
                ("workflowstep-defer", "Freischaltverz\xc3\xb6gerung"),
                ("attributname", "Attributname"),
                ("accesstype", "Zugriffsattribut"),
            ],
           "en":
            [
                ("workflowstep-defer", "Defer-Field"),
                ("attributname", "Attributename"),
                ("accesstype", "Access attribute"),
            ]
            }
