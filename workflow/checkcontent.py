# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal as _tal

from core import db as _db
from .workflow import WorkflowStep, registerStep
from utils.utils import checkXMLString, suppress
import utils.mail as mail


def register():
    registerStep("workflowstep_checkcontent")


class WorkflowStep_CheckContent(WorkflowStep):

    default_settings = dict(
        recipient="",
        sender="",
        subject="",
        text="",
    )

    def runAction(self, node, op=""):
        xml = u'<?xml version="1.0" encoding="UTF-8"?><tag>{}</tag>'.format("".join(node.attrs.itervalues()))
        if not checkXMLString(xml):
            with suppress(Exception, warn=False):
                mail.sendmail(
                        mail.EmailAddress(self.settings['sender'], None),
                        (mail.EmailAddress(self.settings['recipient'], None),),
                        self.settings['subject'],
                        self.settings['text'],
                    )

        self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/checkcontent.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert frozenset(data) == frozenset(("recipient", "sender", "subject", "text"))
        self.settings = data
        _db.session.commit()
