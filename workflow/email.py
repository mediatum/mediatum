"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

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
import core.tree as tree
from workflow import WorkflowStep
import core.athana as athana
from core.translation import t,lang
from utils.utils import formatException
import core.config as config
import logging
import utils.mail as mail

class MailError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def getTALtext(text, context):
    text = '<body xmlns:tal="http://xml.zope.org/namespaces/tal">'+text+'</body>'
    text = athana.getTALstr(text, context)
    text = text.replace("<body>","").replace("</body>","").replace("<body/>","")
    return text

class WorkflowStep_SendEmail(WorkflowStep):
    def sendOut(self, node):
        xfrom = node.get("mailtmp.from")
        to = node.get("mailtmp.to")
        subject = node.get("mailtmp.subject")
        text = node.get("mailtmp.text")
        try:
            log.info("sending mail to %s (%s)" % (to,self.get("email")))
            if not to:
                raise MailError("No receiver address defined")
            if not xfrom:
                raise MailError("No from address defined")
            mail.sendmail(xfrom, to, subject, text)
        except:
            node.set("mailtmp.error",formatException())
            log.info("Error while sending mail- node stays in workflowstep "+self.id+" "+self.name)
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
        link = "http://"+config.get("host.name")+"/pnode?id="+node.id+"&key="+node.get("key")
        link2 = "http://"+config.get("host.name")+"/node?id="+node.id
        try:
            node.set("mailtmp.from", getTALtext(self.get("from"), {"node":node, "link":link, "publiclink":link2}).replace("\n","").strip())
            
            if "@" in self.get('email'):
                print "use given email", self.get("email")
                node.set("mailtmp.to", getTALtext(self.get("email"), {"node":node, "link":link, "publiclink":link2}).replace("\n","").strip())
            elif "@" in node.get(self.get("email")):
                print "use email address from attribute", self.get("email"), node.get(self.get("email"))
                node.set("mailtmp.to", getTALtext(node.get(self.get("email")), {"node":node, "link":link, "publiclink":link2}).replace("\n","").strip())
            
            
            
            node.set("mailtmp.subject", getTALtext(self.get("subject"), {"node":node, "link":link, "publiclink":link2}).replace("\n","").strip())
            node.set("mailtmp.text", getTALtext(self.get("text"), {"node":node, "link":link, "publiclink":link2}))
        except:
            node.set("mailtmp.talerror",formatException())
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
        elif node.get("mailtmp.talerror"):
            node.removeAttribute("mailtmp.talerror")
            self.runAction(node,"true")
            if node.get("mailtmp.talerror"):
                return """<pre>%s</pre>""" % node.get("mailtmp.talerror")
            else:
                return self.show_node_big(req)
        elif node.get("mailtmp.error"):           
            result = t(lang(req), "workflow_email_msg_1")+'<br/>'
            result += '<pre>%s</pre><br>' % node.get("mailtmp.error")
            result += '&gt;<a href="' +req.makeSelfLink({"sendout":"true"})+ '">'+t(lang(req), "workflow_email_resend")+'</a>&lt;'
            return result
        else:
            xfrom = node.get("mailtmp.from")
            to = node.get("mailtmp.to")
            text = node.get("mailtmp.text")
            subject = node.get("mailtmp.subject")
            return req.getTAL("workflow/email.html", {"page":"node?id="+self.id+"&obj="+node.id, "from":xfrom, "to":to, "text":text, "subject":subject}, macro="sendmail")

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

        return ret

