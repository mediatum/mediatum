# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal as _tal

from core import db as _db
from .workflow import WorkflowStep, registerStep
from utils.utils import checkXMLString, suppress
import core.translation as _core_translation
import utils.mail as mail
from schema.schema import Metafield


def register():
    #tree.registerNodeClass("workflowstep-checkcontent", WorkflowStep_CheckContent)
    registerStep("workflowstep_checkcontent")
    _core_translation.addLabels(WorkflowStep_CheckContent.getLabels())


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

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            dict(
                sender=self.get('from'),
                email=self.get('email'),
                subject=self.get('subject'),
                text=self.get('text'),
            ),
            file="workflow/checkcontent.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        for attr in ('email', 'subject', 'text'):
            self.set(attr, data.pop(attr))
        self.set('from', data.pop('sender'))
        assert not data
        _db.session.commit()

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
