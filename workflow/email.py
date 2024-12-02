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

import utils.mail as mail
from core import db

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

    def runAction(self, node, op=""):

        context = dict(
            language=node.get("system.wflanguage"),
            link=_urlparse.urljoin(_flask.request.host_url, "/pnode?id={}&key={}".format(node.id, node.get("key"))),
            node=node,
            publiclink=_urlparse.urljoin(_flask.request.host_url, "/node?id={}".format(node.id)),
        )

        def tal_renderer(text_):
            return None if text_ is None else _tal.getTALstr(text_, context).replace('\n', '').strip()

        from_envelope = tal_renderer(self.settings["from_envelope"])
        from_email = mail.EmailAddress(tal_renderer(self.settings["from_email"]), tal_renderer(self.settings["from_name"]))
        recipients = map(tal_renderer, self.settings['recipient'])
        subject = tal_renderer(self.settings["subject"])
        text = tal_renderer(self.settings["text"])
        reply_to_email = tal_renderer(self.settings["reply_to_email"])
        reply_to_name = tal_renderer(self.settings["reply_to_name"])
        if self.settings["attach_pdf_form"]:
            attachments = {f.abspath.split("_")[-1]: f.abspath for f in node.files if
                           f.filetype == "wfstep-addformpage"}
        else:
            attachments = {}
        mail.sendmail(
            from_email,
            tuple(mail.EmailAddress(r, None) for r in recipients),
            subject,
            text,
            from_envelope,
            attachments=attachments,
            reply_to=mail.EmailAddress(reply_to_email, reply_to_name) if reply_to_email else None,
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
