# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Peter Heckl <heckl@ub.tum.de>

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

import logging
import os.path
from .workflow import WorkflowStep, registerStep
from mediatumtal import tal
from core.translation import t, lang, addLabels
from utils.utils import formatException
import core.config as config
import utils.mail as mail
from core import db
from schema.schema import Metafield

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-send_email", WorkflowStep_SendEmail)
    registerStep("workflowstep_sendemail")
    addLabels(WorkflowStep_SendEmail.getLabels())


class MailError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def getTALtext(text, context):
    #text = tal.getTALstr('<body xmlns:tal="http://xml.zope.org/namespaces/tal">%s</body>' %(text), context)
    #text = text.replace("<body>","").replace("</body>","").replace("<body/>","")
    # return text.replace("\n","").strip()
    return tal.getTALstr(text, context).replace('\n', '').strip()


class WorkflowStep_SendEmail(WorkflowStep):

    def sendOut(self, node):
        xfrom = node.get("system.mailtmp.from")
        to = node.get("system.mailtmp.to")
        sendcondition = self.get("sendcondition")
        attach_pdf_form = bool(self.get("attach_pdf_form"))
        sendOk = 1

        try:
            if sendcondition.startswith("attr:") and "=" in sendcondition:
                arrname, value = sendcondition[5:].split("=")
                if node.get(arrname) != value:
                    sendOk = 0
            elif (sendcondition.startswith("schema=") and node.schema not in sendcondition[7:].split(";")) or (sendcondition.startswith("type=") and not node.get("type") in sendcondition[5:].split(";")) or (sendcondition == "hasfile" and len(node.files) == 0):
                sendOk = 0
        except:
            logg.exception("syntax error in email condition: %s", sendcondition)

        if sendOk:
            try:
                logg.info("sending mail to %s (%s)", to, self.get("email"))
                if not to:
                    raise MailError("No receiver address defined")
                if not xfrom:
                    raise MailError("No from address defined")
                attachments_paths_and_filenames = []
                if attach_pdf_form:
                    pdf_form_files = [f for f in node.files if f.filetype == 'pdf_form']
                    for i, f in enumerate(pdf_form_files):
                        if not os.path.isfile(f.abspath):
                            raise MailError("Attachment file not found: '%s'" % f.abspath)
                        else:
                            #attachments_paths_and_filenames.append((f.retrieveFile(), 'contract_%s_%s.pdf' %(i, node.id)))
                            attachments_paths_and_filenames.append((f.abspath, '%s' % (f.abspath.split('_')[-1])))
                    pass

                mail.sendmail(xfrom, to, node.get("system.mailtmp.subject"), node.get(
                    "system.mailtmp.text"), attachments_paths_and_filenames=attachments_paths_and_filenames)
            except:
                node.set("system.mailtmp.error", formatException())
                db.session.commit()
                logg.exception("Error while sending mail- node stays in workflowstep %s %s", self.id, self.name)
                return
        else:
            logg.info("sending mail prevented by condition %s " % (sendcondition))
            return
        for s in ["mailtmp.from", "mailtmp.to", "mailtmp.subject", "mailtmp.text",
                  "mailtmp.error", "mailtmp.talerror", "mailtmp.send"]:
            try:
                del node.system_attrs[s]
            except KeyError:
                continue

        db.session.commit()
        return 1

    def runAction(self, node, op=""):
        link = "https://%s/pnode?id=%s&key=%s" % (config.get("host.name"), node.id, node.get("key"))
        link2 = "https://%s/node?id=%s" % (config.get("host.name"), node.id)
        attrs = {"node": node, "link": link, "publiclink": link2}
        try:
            if "@" in self.get('from'):
                node.set("system.mailtmp.from", getTALtext(self.get("from"), attrs))
            elif "@" in node.get(self.get('from')):
                node.set("system.mailtmp.from", getTALtext(node.get(self.get("from")), attrs))

            _mails = []
            for m in self.get('email').split(";"):
                if "@" in m:
                    _mails.append(getTALtext(m, attrs))
                elif "@" in node.get(m):
                    _mails.append(getTALtext(node.get(m), attrs))
            node.set("system.mailtmp.to", ";".join(_mails))

            node.set("system.mailtmp.subject", getTALtext(self.get("subject"), attrs))
            node.set("system.mailtmp.text", getTALtext(self.get("text"), attrs))
            db.session.commit()
        except:
            node.system_attrs['mailtmp.talerror'] = formatException()
            db.session.commit()
            return
        if self.get("allowedit").lower().startswith("n"):
            if(self.sendOut(node)):
                self.forward(node, True)

    def show_workflow_node(self, node, req):
        if "sendout" in req.params:
            del req.params["sendout"]
            if "from" in req.params:
                node.set("system.mailtmp.from", req.params.get("from"))
            if "to" in req.params:
                node.set("system.mailtmp.to", req.params.get("to"))
            if "subject" in req.params:
                node.set("system.mailtmp.subject", req.params.get("subject"))
            if "text" in req.params:
                node.set("system.mailtmp.text", req.params.get("text"))
            db.session.commit()
            if(self.sendOut(node)):
                return self.forwardAndShow(node, True, req)
            else:
                return self.show_node_big(req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        elif node.system_attrs.get("mailtmp.talerror", "") != "":
            del node.system_attrs["mailtmp.talerror"]
            db.session.commit()
            self.runAction(node, "true")
            if node.system_attrs.get("mailtmp.talerror", "") != "":
                return """<pre>%s</pre>""" % node.system_attrs.get("mailtmp.talerror")
            else:
                return self.show_node_big(req)
        elif node.get("system.mailtmp.error"):
            return '%s<br/><pre>%s</pre><br>&gt;<a href="%s">%s</a>&lt;' % (t(lang(req), "workflow_email_msg_1"), node.get(
                "system.mailtmp.error"), req.makeSelfLink({"sendout": "true"}), t(lang(req), "workflow_email_resend"))
        else:
            xfrom = node.get("system.mailtmp.from")
            to = node.get("system.mailtmp.to")
            text = node.get("system.mailtmp.text")
            subject = tal.getTALstr(node.get("system.mailtmp.subject"), {}, language=node.get("system.wflanguage"))
            return req.getTAL("workflow/email.html", {"page": u"node?id={}&obj={}".format(self.id, node.id),
                                                      "from": xfrom,
                                                      "to": to,
                                                      "text": text,
                                                      "subject": subject,
                                                      "node": node,
                                                      "sendcondition": self.get("sendcondition"),
                                                      "wfnode": self,
                                                      "pretext": self.getPreText(lang(req)),
                                                      "posttext": self.getPostText(lang(req))},
                              macro="sendmail")

    def metaFields(self, lang=None):
        ret = list()
        field = Metafield("from")
        field.set("label", t(lang, "admin_wfstep_email_sender"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("email")
        field.set("label", t(lang, "admin_wfstep_email_recipient"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("subject")
        field.set("label", t(lang, "admin_wfstep_email_subject"))
        field.set("type", "memo")
        ret.append(field)

        field = Metafield("text")
        field.set("label", t(lang, "admin_wfstep_email_text"))
        field.set("type", "memo")
        ret.append(field)

        field = Metafield("allowedit")
        field.set("label", t(lang, "admin_wfstep_email_text_editable"))
        field.set("type", "list")
        field.set("valuelist", t(lang, "admin_wfstep_email_text_editable_options"))
        ret.append(field)

        field = Metafield("sendcondition")
        field.set("label", t(lang, "admin_wfstep_email_sendcondition"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("attach_pdf_form")
        field.set("label", t(lang, "workflowstep-email_label_attach_pdf_form"))
        field.set("type", "check")
        ret.append(field)
        return ret

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
