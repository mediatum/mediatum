# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import os.path
import urlparse as _urlparse

import flask as _flask

from .workflow import WorkflowStep, registerStep
from mediatumtal import tal as _tal

from utils.utils import formatException
import core.csrfform as _core_csrfform
import core.translation as _core_translation
import utils.mail as mail
from core import db
from schema.schema import Metafield
from core.request_handler import makeSelfLink as _makeSelfLink

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-send_email", WorkflowStep_SendEmail)
    registerStep("workflowstep_sendemail")
    _core_translation.addLabels(WorkflowStep_SendEmail.getLabels())


class MailError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def getTALtext(text, context):
    #text = tal.getTALstr('<body xmlns:tal="http://xml.zope.org/namespaces/tal">%s</body>' %(text), context)
    #text = text.replace("<body>","").replace("</body>","").replace("<body/>","")
    # return text.replace("\n","").strip()
    return _tal.getTALstr(text, context).replace('\n', '').strip()


class WorkflowStep_SendEmail(WorkflowStep):

    default_settings = dict(
        allowedit=False,
        attach_pdf_form=False,
        recipient=(),
        sender="",
        subject="",
        text="",
    )

    def sendOut(self, node):
        xfrom = node.get("system.mailtmp.from")
        recipient = node.get("system.mailtmp.to")

        try:
            logg.info("sending mail to %s (%s)", recipient, " , ".join(self.settings["recipient"]))
            if not recipient:
                raise MailError("No receiver address defined")
            if not xfrom:
                raise MailError("No from address defined")
            attachments_paths_and_filenames = []
            if self.settings["attach_pdf_form"]:
                for f in node.files:
                    if f.filetype != 'wfstep-addformpage':
                        continue
                    if not os.path.isfile(f.abspath):
                        raise MailError("Attachment file not found: '%s'" % f.abspath)
                    attachments_paths_and_filenames.append((f.abspath, f.abspath.split('_')[-1]))

            mail.sendmail(xfrom, recipient, node.get("system.mailtmp.subject"), node.get(
                "system.mailtmp.text"), attachments_paths_and_filenames=attachments_paths_and_filenames)
        except:
            node.set("system.mailtmp.error", formatException())
            db.session.commit()
            logg.exception("Error while sending mail- node stays in workflowstep %s %s", self.id, self.name)
            return

        for s in ["mailtmp.from", "mailtmp.to", "mailtmp.subject", "mailtmp.text",
                  "mailtmp.error", "mailtmp.send"]:
            try:
                del node.system_attrs[s]
            except KeyError:
                continue

        db.session.commit()
        return 1

    def runAction(self, node, op=""):
        link = _urlparse.urljoin(_flask.request.host_url, "/pnode?id={}&key={}".format(node.id, node.get("key")))
        link2 = _urlparse.urljoin(_flask.request.host_url, "/node?id={}".format(node.id))
        attrs = {"node": node, "link": link, "publiclink": link2}
        sender = self.settings['sender']
        if "@" in sender:
            node.set("system.mailtmp.from", getTALtext(sender, attrs))
        elif "@" in node.get(sender):
            node.set("system.mailtmp.from", getTALtext(node.get(sender), attrs))

        _mails = []
        for m in self.settings['recipient']:
            if "@" in m:
                _mails.append(getTALtext(m, attrs))
            elif "@" in node.get(m):
                _mails.append(getTALtext(node.get(m), attrs))
        node.set("system.mailtmp.to", ";".join(_mails))

        node.set("system.mailtmp.subject", getTALtext(self.settings["subject"], attrs))
        node.set("system.mailtmp.text", getTALtext(self.settings["text"], attrs))
        db.session.commit()
        if not self.settings["allowedit"]:
            if(self.sendOut(node)):
                self.forward(node, True)

    def show_workflow_node(self, node, req):
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
            return u'{}<br/><pre>{}</pre><br/>&gt;<a href="{}">{}</a>&lt;'.format(
                    _core_translation.translate(_core_translation.set_language(req.accept_languages), "workflow_email_msg_1"),
                    node.get("system.mailtmp.error"),
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
                        subject=_tal.getTALstr(
                            node.get("system.mailtmp.subject"),
                            {},
                            language=node.get("system.wflanguage"),
                           ),
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

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-email_label_attach_pdf_form", "PDF-Form als Anhang senden"),
                    ("workflowstep-email_label_header", "Email versenden"),
                    ("workflowstep-email_label_sender", "Von"),
                    ("workflowstep-email_label_recipient", "An"),
                    ("workflowstep-email_label_subject", "Betreff"),
                    ("workflowstep-email_label_text", "Nachricht"),
                    ("workflowstep-email_label_send", "Absenden"),
                    ("workflowstep-email_label_reset", u"Zurücksetzen"),

                ],
                "en":
                [
                    ("workflowstep-email_label_attach_pdf_form", "Send PDF from as attachment"),
                    ("workflowstep-email_label_header", "Send Email"),
                    ("workflowstep-email_label_sender", "From"),
                    ("workflowstep-email_label_recipient", "To"),
                    ("workflowstep-email_label_subject", "Subject"),
                    ("workflowstep-email_label_text", "Message"),
                    ("workflowstep-email_label_send", "Send"),
                    ("workflowstep-email_label_reset", "Reset"),
                ]
                }
