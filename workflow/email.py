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
        allowedit=False,
        attach_pdf_form=False,
        recipient=(),
        sender="",
        subject="",
        text="",
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
            return _tal.getTALstr(text, context).replace('\n', '').strip()

        return renderer

    def send_email(self, node, sender, recipients, subject, text):
        try:
            if not recipients:
                raise RuntimeError("No receiver address defined")
            if not sender:
                raise RuntimeError("No from address defined")
            if self.settings["attach_pdf_form"]:
                attachments = {f.abspath.split("_")[-1]:f.abspath for f in node.files if f.filetype=="wfstep-addformpage"}
            else:
                attachments = {}
            mail.sendmail(sender, recipients, subject, text, attachments=attachments)
        except:
            logg.exception("Error while sending mail- node stays in workflowstep %s %s", self.id, self.name)
            raise

    def runAction(self, node, op=""):
        if self.settings["allowedit"]:
            return
        tal_renderer = self.get_tal_renderer(node, node.get("system.wflanguage"))
        sender = tal_renderer(self.settings['sender'])
        recipients = map(tal_renderer, self.settings['recipient'])
        subject = tal_renderer(self.settings["subject"])
        text = tal_renderer(self.settings["text"])
        try:
            self.send_email(
                node,
                mail.EmailAddress(sender, None),
                tuple(mail.EmailAddress(r, None) for r in recipients),
                subject,
                text,
            )
        except:
            # Will raise later in 'show_workflow_node'
            pass
        else:
            self.forward(node, True)

    def show_workflow_node(self, node, req):
        if not self.settings["allowedit"]:
            raise RuntimeError("editing unsent email not allowed")

        tal_renderer = self.get_tal_renderer(
                node, node.get("system.wflanguage") or _core_translation.set_language(req.accept_languages),
            )

        sender = req.values["sender"] if "sender" in req.values else tal_renderer(self.settings['sender'])
        recipient = (req.values["recipient"].split(";") if "recipient" in
                    req.values else map(tal_renderer, self.settings['recipient']))
        subject = req.values["subject"] if "subject" in req.values else tal_renderer(self.settings["subject"])
        text = req.values["text"] if "text" in req.values else tal_renderer(self.settings["text"])

        if "sendout" in req.params:
            del req.params["sendout"]
            try:
                self.send_email(
                    node,
                    mail.EmailAddress(sender, None),
                    tuple(mail.EmailAddress(r, None) for r in recipient)),
                    subject,
                    text,
                )
            except:
                return u'{} &gt;<a href="{}">{}</a>&lt;'.format(
                        _core_translation.translate(
                            _core_translation.set_language(req.accept_languages),
                            "workflow_email_msg_1",
                        ),
                        _makeSelfLink(req, {"sendout": "true"}),
                        _core_translation.translate(
                            _core_translation.set_language(req.accept_languages),
                            "workflow_email_resend",
                        ),
                    )
            else:
                return self.forwardAndShow(node, True, req)

        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)
        else:
            return _tal.processTAL(
                    dict(
                        page=u"node?id={}&obj={}".format(self.id, node.id),
                        sender=sender,
                        recipient=recipient,
                        text=text,
                        subject=subject,
                        node=node,
                        wfnode=self,
                        pretext=self.getPreText(_core_translation.set_language(req.accept_languages)),
                        posttext=self.getPostText(_core_translation.set_language(req.accept_languages)),
                        csrf=_core_csrfform.get_token(),
                    ),
                    file="workflow/email.html",
                    macro="sendmail",
                    request=req,
                )

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/email.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        for attr in ("allowedit", "attach_pdf_form"):
            data[attr] = bool(data.get(attr))
        data["recipient"] = filter(None, (s.strip() for s in data["recipient"].split("\r\n")))
        assert frozenset(data) == frozenset(("allowedit", "attach_pdf_form", "recipient", "sender", "subject", "text"))
        self.settings = data
        db.session.commit()
