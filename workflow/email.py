# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import urlparse as _urlparse

import flask as _flask

from .workflow import WorkflowStep, registerStep
from mediatumtal import tal as _tal

from utils.utils import formatException
import core.csrfform as _core_csrfform
import core.translation as _core_translation
import utils.mail as mail
from core import db
from core.request_handler import makeSelfLink as _makeSelfLink

logg = logging.getLogger(__name__)


def register():
    registerStep("workflowstep_sendemail")


class WorkflowStep_SendEmail(WorkflowStep):

    default_settings = dict(
        attach_pdf_form=False,
        recipient=(),
        from_email="",
        from_name=None,
        from_envelope=None,
        reply_to_email=None,
        reply_to_name=None,
        subject=None,
        text=None,
    )

    def get_tal_renderer(self, node, language):
        context = dict(
                node=node,
                link=_urlparse.urljoin(_flask.request.host_url, "/pnode?id={}&key={}".format(node.id, node.get("key"))),
                publiclink=_urlparse.urljoin(_flask.request.host_url, "/node?id={}".format(node.id)),
            )
        if language:
            context["language"] = language

        def renderer(text):
            return None if text is None else _tal.getTALstr(text, context).replace('\n', '').strip()

        return renderer

    def send_email(self, node, sender, recipients, subject, text, envelope_sender_address=None, reply_to=None):
        try:
            if not recipients:
                raise RuntimeError("No receiver address defined")
            if not sender:
                raise RuntimeError("No from address defined")
            if self.settings["attach_pdf_form"]:
                attachments = {f.abspath.split("_")[-1]:f.abspath for f in node.files if f.filetype=="wfstep-addformpage"}
            else:
                attachments = {}
            mail.sendmail(sender, recipients, subject, text, envelope_sender_address, attachments=attachments, reply_to=reply_to)
        except:
            logg.exception("Error while sending mail- node stays in workflowstep %s %s", self.id, self.name)
            raise

    def runAction(self, node, op=""):
        tal_renderer = self.get_tal_renderer(node, node.get("system.wflanguage"))

        from_envelope = tal_renderer(self.settings["from_envelope"])
        from_email = mail.EmailAddress(tal_renderer(self.settings["from_email"]), tal_renderer(self.settings["from_name"]))
        recipients = map(tal_renderer, self.settings['recipient'])
        subject = tal_renderer(self.settings["subject"])
        text = tal_renderer(self.settings["text"])
        reply_to_email = tal_renderer(self.settings["reply_to_email"])
        reply_to_name = tal_renderer(self.settings["reply_to_name"])
        self.send_email(
            node,
            from_email,
            tuple(mail.EmailAddress(r, None) for r in recipients),
            subject,
            text,
            from_envelope,
            mail.EmailAddress(reply_to_email, reply_to_name) if reply_to_email else None,
        )
        self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/email.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        data["attach_pdf_form"] = bool(data.get("attach_pdf_form"))
        assert frozenset(data) == frozenset((
            "attach_pdf_form",
            "recipient",
            "from_email",
            "from_name",
            "from_envelope",
            "reply_to_email",
            "reply_to_name",
            "subject",
            "text",
        ))
        data["recipient"] = filter(None, (s.strip() for s in data["recipient"].split("\r\n")))
        for attr in ("from_name", "from_envelope", "reply_to_email", "reply_to_name"):
            data[attr] = data[attr] or None
        self.settings = data
        db.session.commit()
