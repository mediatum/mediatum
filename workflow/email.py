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


    def sendOut(self, node):
        xfrom = node.get("system.mailtmp.from")
        recipients = node.get("system.mailtmp.to")
        try:
            logg.info("sending mail to %s", recipients)
            if not recipients:
                raise RuntimeError("No receiver address defined")
            if not xfrom:
                raise RuntimeError("No from address defined")
            if self.settings["attach_pdf_form"]:
                attachments = {f.abspath.split("_")[-1]:f.abspath for f in node.files if f.filetype=="wfstep-addformpage"}
            else:
                attachments = {}
            mail.sendmail(
                mail.EmailAddress(xfrom, None),
                tuple(mail.EmailAddress(r, None) for r in recipients.split(";")),
                node.get("system.mailtmp.subject"),
                node.get("system.mailtmp.text"),
                attachments=attachments,
            )
        except:
            node.set("system.mailtmp.error", "1")
            db.session.commit()
            logg.exception("Error while sending mail- node stays in workflowstep %s %s", self.id, self.name)
            return

        for s in ("from", "to", "subject", "text", "error", "send"):
            node.system_attrs.pop("mailtmp.{}".format(s), None)

        db.session.commit()
        return 1

    def runAction(self, node, op=""):
        tal_renderer = self.get_tal_renderer(node, node.get("system.wflanguage"))
        sender = self.settings['sender']
        if "@" in sender:
            node.set("system.mailtmp.from", tal_renderer(sender))
        elif "@" in node.get(sender):
            node.set("system.mailtmp.from", tal_renderer(node.get(sender)))

        _mails = []
        for m in self.settings['recipient']:
            if "@" in m:
                _mails.append(tal_renderer(m))
            elif "@" in node.get(m):
                _mails.append(tal_renderer(node.get(m)))
        node.set("system.mailtmp.to", ";".join(_mails))
        node.set("system.mailtmp.subject", tal_renderer(self.settings["subject"], node.get("system.wflanguage")))
        node.set("system.mailtmp.text", tal_renderer(self.settings["text"]))
        db.session.commit()
        if not self.settings["allowedit"]:
            if(self.sendOut(node)):
                self.forward(node, True)

    def show_workflow_node(self, node, req):
        if not self.settings["allowedit"]:
            raise RuntimeError("editing unsent email not allowed")
        if "sendout" in req.params:
            del req.params["sendout"]
            if "sender" in req.params:
                node.set("system.mailtmp.from", req.params.get("sender"))
            if "recipient" in req.params:
                node.set("system.mailtmp.to", req.params.get("recipient"))
            if "subject" in req.params:
                node.set("system.mailtmp.subject", req.params.get("subject"))
            if "text" in req.params:
                node.set("system.mailtmp.text", req.params.get("text"))
            db.session.commit()
            if(self.sendOut(node)):
                return self.forwardAndShow(node, True, req)

        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        elif node.get("system.mailtmp.error"):
            return u'{} &gt;<a href="{}" class="mediatum-link-mediatum">{}</a>&lt;'.format(
                    _core_translation.translate(_core_translation.set_language(req.accept_languages), "workflow_email_msg_1"),
                    _makeSelfLink(req, {"sendout": "true"}),
                    _core_translation.translate(_core_translation.set_language(req.accept_languages), "workflow_email_resend"),
                )
        else:
            return _tal.processTAL(
                    dict(
                        page=u"node?id={}&obj={}".format(self.id, node.id),
                        sender=node.get("system.mailtmp.from"),
                        recipient=node.get("system.mailtmp.to"),
                        text=node.get("system.mailtmp.text"),
                        subject=node.get("system.mailtmp.subject"),
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
