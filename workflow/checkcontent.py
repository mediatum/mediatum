# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from .workflow import WorkflowStep, registerStep
from utils.utils import checkXMLString, suppress
from core.translation import t, lang, addLabels
import utils.mail as mail
from schema.schema import Metafield


def register():
    #tree.registerNodeClass("workflowstep-checkcontent", WorkflowStep_CheckContent)
    registerStep("workflowstep_checkcontent")
    addLabels(WorkflowStep_CheckContent.getLabels())


class MailError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class WorkflowStep_CheckContent(WorkflowStep):

    def runAction(self, node, op=""):
        attrs = ""
        for k, v in node.attrs.items():
            attrs += v
        if not checkXMLString(u'<?xml version="1.0" encoding="UTF-8"?>' + u'<tag>' + attrs + u'</tag>'):
            with suppress(Exception, warn=False):
                mail.sendmail(self.get('from'), self.get('to'), self.get('subject'), self.get('text'))

        self.forward(node, True)

    def metaFields(self, lang=None):
        ret = []
        field = Metafield("from")
        field.set("label", t(lang, "admin_wfstep_checkcontent_sender"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("email")
        field.set("label", t(lang, "admin_wfstep_checkcontent_recipient"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("subject")
        field.set("label", t(lang, "admin_wfstep_checkcontent_subject"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("text")
        field.set("label", t(lang, "admin_wfstep_checkcontent_text"))
        field.set("type", "memo")
        ret.append(field)

        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-checkcontent", u"Inhalt Prüfen"),
                    ("admin_wfstep_checkcontent_sender", "E-Mail Absender"),
                    ("admin_wfstep_checkcontent_recipient", u"Empfänger"),
                    ("admin_wfstep_checkcontent_subject", "Betreff"),
                    ("admin_wfstep_checkcontent_text", "Text"),
                ],
                "en":
                [
                    ("workflowstep-checkcontent", "Check Content"),
                    ("admin_wfstep_checkcontent_sender", "Email Sender"),
                    ("admin_wfstep_checkcontent_recipient", "Recipient"),
                    ("admin_wfstep_checkcontent_subject", "Subject"),
                    ("admin_wfstep_checkcontent_text", "Text"),
                ]
                }
