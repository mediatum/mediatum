# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

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
