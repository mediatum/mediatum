"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Arne Seifert <arne.seifert@tum.de>

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

from .workflow import WorkflowStep, registerStep, addLabels
from core.translation import t
from core import db
from schema.schema import Metafield


def register():
    #tree.registerNodeClass("workflowstep-deletefile", WorkflowStep_DeleteFile)
    registerStep("workflowstep_deletefile")
    addLabels(getLabels())


class WorkflowStep_DeleteFile(WorkflowStep):

    def runAction(self, node, op=""):
        if self.get('filetype') == '*':  # delete all files
            for f in node.files:
                node.files.remove(f)

        elif self.get('filetype') != '':
            types = self.get('filetype').split(';')
            for f in node.files:
                if f.filetype in types:
                    node.files.remove(f)
        self.forward(node, True)
        db.session.commit()

    def metaFields(self, lang=None):
        field = Metafield("filetype")
        field.set("label", t(lang, "admin_wfstep_deletefiletype"))
        field.set("type", "text")
        return [field]


def getLabels(key=None, lang=None):
    return {"de":
            [
                ("workflowstep-deletefile", "Datei entfernen"),
                ("admin_wfstep_deletefiletype", "Dateityp"),
            ],
            "en":
            [
                ("workflowstep-deletefile", "Remove file"),
                ("admin_wfstep_deletefiletype", "File type"),
            ]
            }
