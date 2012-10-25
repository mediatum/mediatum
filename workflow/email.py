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

import os.path
import core.tree as tree
from workflow import WorkflowStep
import core.athana as athana
from core.translation import t,lang
from utils.utils import formatException
import core.config as config
import logging
import utils.mail as mail
log = logging.getLogger('backend')

class MailError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def getTALtext(text, context):
    text = athana.getTALstr('<body xmlns:tal="http://xml.zope.org/namespaces/tal">'+text+'</body>', context)
    text = text.replace("<body>","").replace("</body>","").replace("<body/>","")
    return text.replace("\n","").strip()

class WorkflowStep_SendEmail(WorkflowStep):
    def sendOut(self, node):
        xfrom = node.get("mailtmp.from")
        to = node.get("mailtmp.to")
        sendcondition = self.get("sendcondition")
        attach_pdf_form = bool(self.get("attach_pdf_form"))
        sendOk = 1
        
        try:
            if sendcondition.startswith("attr:") and "=" in sendcondition:
                arrname, value = sendcondition[5:].split("=")
                if node.get(arrname)!=value:
                    sendOk = 0
            elif (sendcondition.startswith("schema=") and node.getSchema() not in sendcondition[7:].split(";")) or (sendcondition.startswith("type=") and not node.get("type") in sendcondition[5:].split(";")) or (sendcondition=="hasfile" and len(node.getFiles())==0):
                sendOk = 0
        except:
            log.info("syntax error in email condition: %s" %(sendcondition))
            
        if sendOk:
            try:
                log.info("sending mail to %s (%s)" %(to, self.get("email")))
                if not to:
                    raise MailError("No receiver address defined")
                if not xfrom:
                    raise MailError("No from address defined")
                attachments_paths_and_filenames = []    
                if attach_pdf_form:
                    for f in node.getFiles():
                        print f, f.getName(), f.getType(), f.retrieveFile()
                    pdf_form_files = [f for f in node.getFiles() if f.getType() == 'pdf_form']
                    for i, f in enumerate(pdf_form_files):
                        if not os.path.isfile(f.retrieveFile()):
                            raise MailError("Attachment file not found: '%s'" % f.retrieveFile())
                        else:
                            attachments_paths_and_filenames.append((f.retrieveFile(), 'contract_' + str(i) + '_' + str(node.id) + '.pdf'))
                    pass        
                    #attachments_paths_and_filenames = [(f.retrieveFile(), 'contract_' + str(node.id) + '.pdf') for f in pdf_form_files]
                print '----> attachments_paths_and_filenames:', attachments_paths_and_filenames    
                mail.sendmail(xfrom, to, node.get("mailtmp.subject"), node.get("mailtmp.text"), attachments_paths_and_filenames=attachments_paths_and_filenames)
            except:
                node.set("mailtmp.error", formatException())
                log.info("Error while sending mail- node stays in workflowstep %s %s" %(self.id, self.name))
                return
        else:
            log.info("sending mail prevented by condition %s " %(sendcondition))
            return
            
        node.removeAttribute("mailtmp.send")
        node.removeAttribute("mailtmp.from")
        node.removeAttribute("mailtmp.to")
        node.removeAttribute("mailtmp.subject")
        node.removeAttribute("mailtmp.text")
        node.removeAttribute("mailtmp.error")
        node.removeAttribute("mailtmp.talerror")
        return 1

    def runAction(self, node, op=""):
        link = "http://%s/pnode?id=%s&key=%s" %(config.get("host.name"), node.id, node.get("key"))
        link2 = "http://%s/node?id=%s" %(config.get("host.name"), node.id)
        attrs = {"node":node, "link":link, "publiclink":link2}
        try:
            if "@" in self.get('from'):
                node.set("mailtmp.from", getTALtext(self.get("from"), attrs))
            elif "@" in node.get(self.get('from')):
                node.set("mailtmp.from", getTALtext(node.get(self.get("from")), attrs))

            if "@" in self.get('email'):
                node.set("mailtmp.to", getTALtext(self.get("email"), attrs))
            elif "@" in node.get(self.get("email")):
                node.set("mailtmp.to", getTALtext(node.get(self.get("email")), attrs))

            node.set("mailtmp.subject", getTALtext(self.get("subject"), attrs))
            node.set("mailtmp.text", getTALtext(self.get("text"), attrs))
        except:
            node.set("mailtmp.talerror", formatException())
            return
        if self.get("allowedit").lower().startswith("n"):
            if(self.sendOut(node)):
                self.forward(node, True)

    def show_workflow_node(self, node, req):
        if "sendout" in req.params:
            del req.params["sendout"]
            if "from" in req.params:
                node.set("mailtmp.from", req.params.get("from"))
            if "to" in req.params:
                node.set("mailtmp.to", req.params.get("to"))
            if "subject" in req.params:
                node.set("mailtmp.subject", req.params.get("subject"))
            if "text" in req.params:
                node.set("mailtmp.text", req.params.get("text"))
            if(self.sendOut(node)):
                return self.forwardAndShow(node, True, req)
            else:
                return self.show_node_big(req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)
            
        
        elif node.get("mailtmp.talerror"):
            node.removeAttribute("mailtmp.talerror")
            self.runAction(node, "true")
            if node.get("mailtmp.talerror"):
                return """<pre>%s</pre>""" % node.get("mailtmp.talerror")
            else:
                return self.show_node_big(req)
        elif node.get("mailtmp.error"):
            return '%s<br/><pre>%s</pre><br>&gt;<a href="%s">%s</a>&lt;' %(t(lang(req), "workflow_email_msg_1"), node.get("mailtmp.error"), req.makeSelfLink({"sendout":"true"}), t(lang(req), "workflow_email_resend"))
        else:
            xfrom = node.get("mailtmp.from")
            to = node.get("mailtmp.to")
            text = node.get("mailtmp.text")
            subject = node.get("mailtmp.subject")
            return req.getTAL("workflow/email.html", {"page":"node?id="+self.id+"&obj="+node.id, "from":xfrom, "to":to, "text":text, "subject":subject, "node":node, "sendcondition":self.get("sendcondition"), "wfnode":self}, macro="sendmail")

    def metaFields(self, lang=None):
        ret = list()
        field = tree.Node("from", "metafield")
        field.set("label", t(lang, "admin_wfstep_email_sender"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("email", "metafield")
        field.set("label", t(lang, "admin_wfstep_email_recipient"))
        field.set("type", "text")
        ret.append(field)
        
        field = tree.Node("subject", "metafield")
        field.set("label", t(lang, "admin_wfstep_email_subject"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("text", "metafield")
        field.set("label", t(lang, "admin_wfstep_email_text"))
        field.set("type", "memo")
        ret.append(field)

        field = tree.Node("allowedit", "metafield")
        field.set("label", t(lang, "admin_wfstep_email_text_editable"))
        field.set("type", "list")
        field.set("valuelist", t(lang, "admin_wfstep_email_text_editable_options"))
        ret.append(field)

        field = tree.Node("sendcondition", "metafield")
        field.set("label", t(lang, "admin_wfstep_email_sendcondition"))
        field.set("type", "text")
        ret.append(field)
        
        field = tree.Node("attach_pdf_form", "metafield")
        field.set("label", t(lang, "workflowstep-email_label_attach_pdf_form"))
        field.set("type", "check")
        ret.append(field)              
        
        return ret
        
    def getLabels(self):
        return { "de":
            [
                ("workflowstep-email_label_attach_pdf_form", "PDF-Form als Anhang senden"),
                
            ],
           "en":
            [
                ("workflowstep-email_label_attach_pdf_form", "Send PDF from as attachment"),
            ]
            }        

