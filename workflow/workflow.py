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
from utils import *
import workflows
from workflows import registerStep
import tree
import date
import logging
import config
import acl
import athana
import random
import mail
from metadatatypes import showEditor,parseEditorData,getMetaType,VIEW_HIDE_EMPTY
from translation import t,lang

import fileutils

log = logging.getLogger('backend')

class Workflows(tree.Node):
    def show_node_big(node, req):
        access = acl.AccessData(req)

        list = []
        for workflow in workflows.getWorkflowList():
            if access.hasWriteAccess(workflow):
                list += [workflow]

        return req.getTAL("objtypes/workflow.html", {"list":list}, macro="workflowlist")

    def can_open(node):
        return 1

    def getLabel(node):
        return node.name


class Workflow(tree.Node):
    def show_node_big(node, req):
        access = acl.AccessData(req)
        if not access.hasWriteAccess(node):
            return '<i>' + t(lang(req),"permission_denied") + '</i>'

        return req.getTAL("objtypes/workflow.html", {"workflow": node}, macro="object_list")

    def getId(self):
        return self.getName()
    def setId(self, i):
        self.setName(i)

    def getLink(self):
        return '?id='+self.id

    def show_node_image(node):
        return '<img border="0" src="/img/directory.png">'

    def show_node_text(node, words=None):
        return ""
    
    def can_open(node):
        return 1
    def getLabel(node):
        return node.name
    
    def getName(self):
        return self.name
    def setName(self, n):
        self.setName(n)

    def getDescription(self):
        return self.get("description")
    def setDescription(self, d):
        self.set("description", d)

    def getSteps(self):
        return self.getChildren()

    def getNode(self, type):
        raise ""

    def getStartNode(self):
        followers = {}
        for step in self.getChildren():
            if step.getTrueId():
                followers[step.getTrueId()] = None
            if step.getFalseId():
                followers[step.getFalseId()] = None
        for step in self.getChildren():      	
            if step.id not in followers:
                return step
        return None # circular workflow- shouldn't happen

    def getStep(self, name):
        return self.getChild(name)

    def getNodeList(self):
        list = []
        for step in self.getSteps():
            list += step.getChildren()
        return list

    def addStep(self,step):
        self.addChild(step)
        return step
    

class WorkflowStep(tree.Node):
    
    def getId(self):
        return self.getName()

    def show_node_big(self, req):
        access = acl.AccessData(req)
        if "obj" in req.params:
            node = tree.getNode(req.params["obj"])
            key = req.params.get("key", req.session.get("key", ""))
            req.session["key"] = key

            if not access.hasWriteAccess(self) and \
                (key != node.get("key")): # no permission

                link = '('+self.name+')'
                
                return req.getTAL("objtypes/workflow.html", {"node": node, "link":link, "email":config.get("email.workflow")}, macro="workflow_step")

            present = 0
            for p in node.getParents():
                if p.id == self.id:
                    present = 1
            if present:
                link = req.makeLink("/mask", {"id":self.id})
                if "forcetrue" in req.params:
                    return self.forwardAndShow(node, True, req, link=link)
                if "forcefalse" in req.params:
                    return self.forwardAndShow(node, False, req, link=link)
                if "raw" in req.params:
                    return self.show_workflow_node(node, req)
                else:
                    return '<center>'+self.show_workflow_node(node, req)+'</center>'
            else:
                return '<center>'+self.show_workflow_notexist(node, req)+'</center>'
        else:
            return '<center>'+self.show_workflow_step(req)+'</center>'

    def can_open(self):
        # inhibit several content enrichment features
        return 1

    def show_workflow_notexist(self, node, req):
        step = workflows.getNodeWorkflowStep(node)

        link = ""
        if step:
            link = """/mask?id=%s&obj=%s""" % (step.id,node.id)
            return """<script language="javascript">document.location.href = "%s";</script> <a href="%s">%s</a>""" % (link,link,step.name)
        else:
            return '<i>'+t(lang(req),"permission_denied")+'</i>'


    def show_workflow_node(self, node, req):

        if "gotrue" in req.params:
            return self.forwardAndShow(node, True, req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        # to be overloaded
        return req.getTAL("objtypes/workflow.html", {"node": node, "name":self.name}, macro="workflow_node")
     

    def show_workflow_step(self, req):
        access = acl.AccessData(req)
        if not access.hasWriteAccess(self):
            return '<i>'+t(lang(req),"permission_denied")+'</i>'
        
        return req.getTAL("objtypes/workflow.html", {"step": self, "nodelink": "/mask?id="+self.id+"&obj=", "format_date": date.format_date, "parse_date": date.parse_date}, macro="workflow_show")
    
    def show_node_image(node):
        return """<img border="0" src="/img/directory.png">"""
    
    def show_node_text(node, req, context):
        return ""

    def getLink(self):
        return "/mask?id="+self.id
                
    def getId(self):
        return self.name

    def getType(self):
        return self.getType()
    
    def getLabel(node):
        return node.name

    def isAdminStep(self):
        if self.get("adminstep")=="1":
            return 1
        return 0

    def runAction(self, node, op=""):
        log.error("No Workflow action defined for workflowstep "+self.getId()+" (op="+str(op)+")")

    def forward(self, node, op):
        if op==True:
            op = "true"
        elif op==False:
            op = "false"
        return workflows.runWorkflowStep(node, op)
   
    def forwardAndShow(self, node, op, req, link=None):
        newnode = self.forward(node, op)

        if newnode is None:
            return req.getTAL("objtypes/workflow.html", {"node":node}, macro="workflow_forward")

        if link is None:
            newloc = req.makeLink("/mask", {"id":newnode.id, "obj":node.id})
        else:
            newloc = link
        redirect = 1
        if redirect == 0:
            return req.getTAL("objtypes/workflow.html", {"newnodename":newnode.name, "email":config.get("email.workflow")}, macro="workflow_forward2")
        else:
            return """<script language="javascript">document.location.href = "%s";</script>""" % newloc

    def getTrueId(self):
        id = self.get("truestep")
        return id

    def getFalseId(self):
        id = self.get("falsestep")
        return id

    def getTrueLabel(self):
        return self.get("truelabel")

    def getFalseLabel(self):
        return self.get("falselabel")

    def getTrueFunction(self):
        return self.get("truefunction")

    def getFalseFunction(self):
        return self.get("falsefunction")

    def getComment(self):
        return self.get("comment")

    def metaFields(self):
        return list()

    def tableRowButtons(self, node):
        result = '<tr><td align="left">'
        result += '<input type="hidden" name="id" value="%s"/>' % self.id
        result += '<input type="hidden" name="obj" value="%s"/>' % node.id
        if self.getFalseId():
            result += '<input type="submit" name="gofalse" value="%s"/>' % self.getFalseLabel()
        else:
            result += '&nbsp;'
        result += '</td><td align="right">'
        if self.getTrueId():
            result += '<input type="submit" name="gotrue" value="%s"/>' % self.getTrueLabel()
        else:
            result += '&nbsp;'
        result += '</td></tr>'
        return result

def mkKey():
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    s = ""
    for i in range(0,16):
        s += alphabet[random.randrange(0,len(alphabet)-1)]
    return s

class WorkflowStep_Start(WorkflowStep):
    def show_workflow_step(self, req):

        typename = self.get("newnodetype")

        if "Erstellen" in req.params:
            if typename not in [ty.strip() for ty in self.get("newnodetype").split(";")]:
                return '<i>' + t(lang(req),"permission_denied") + '</i>'
            node = tree.Node(name="", type=typename)
            self.addChild(node)
            node.setAccess("read", "{user workflow}")
            node.set("creator", "workflow-"+self.getParents()[0].getName())
            node.set("creationtime", date.format_date())
            node.set("key", mkKey())
            req.session["key"] = node.get("key")
            return self.forwardAndShow(node, True, req)
       
        types = []
        for a in typename.split(";"):
            if a:
                m = getMetaType(a)
                # we could now check m.isActive(), but for now let's
                # just take all specified metatypes, so that edit area
                # and workflow are independent on this
                types += [m]

        cookie_error = t(lang(req),"Your browser doesn't support cookies")

        js="""
        <script language="javascript">
        function cookie_test() {
            if (document.cookie=="") 
                document.cookie = "CookieTest=Erfolgreich";
            if (document.cookie=="") {
                alert("%s");
            }
        }
        cookie_test();
        </script>""" % cookie_error

        return req.getTAL("objtypes/workflow.html", {"types":types, "id":self.id, "js":js}, macro="workflow_start")
        
    def metaFields(self):
        ret = list()
        field = tree.Node("newnodetype", "metafield")
        field.set("label", "erstellbare Node-Typen (;-separiert)")
        field.set("type", "text")
        ret.append(field)
        return ret

class WorkflowStep_EditMetadata(WorkflowStep):
    def show_workflow_node(self, node, req):
        result = ""
        error = ""
        key = req.params.get("key", req.session.get("key",""))

        maskname = self.get("mask")
        mask = getMetaType(node.type).getMask(maskname)

        if "metaDataEditor" in req.params:
            mask.updateNode([node], req)
            if hasattr(node,"event_metadata_changed"):
                node.event_metadata_changed()
            missing = mask.validate([node])
            print "datum:",  mask.validate([node])
            if not missing or "gofalse" in req.params:
                op = "gotrue" in req.params
                return self.forwardAndShow(node, op, req)
            else:
                error = '<p class="error">'+ t(lang(req),"workflow_error_msg")+'</p>'
                req.params["errorlist"] = missing
        
        return req.getTAL("objtypes/workflow.html", {"name":self.getName(), "error":error, "key":key, "mask":mask.getFormHTML([node],req), "buttons":self.tableRowButtons(node)}, macro="workflow_metadateneditor")
    
    def metaFields(self):
        ret = list()
        field = tree.Node("mask", "metafield")
        field.set("label", "Editor-Maske")
        field.set("type", "text")
        ret.append(field)
        return ret

class WorkflowStep_Publish(WorkflowStep):
    def runAction(self, node, op=""):
        newaccess = []
        a = node.getAccess("read")
        if a:
            for right in a.split(','):
                if right != "{user workflow}":
                    newaccess += [right]
            node.setAccess("read", ",".join(newaccess))
        self.forward(node, True)

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
                raise "No receiver address defined"
            if not xfrom:
                raise "No from address defined"
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
            node.set("mailtmp.to", getTALtext(self.get("email"), {"node":node, "link":link, "publiclink":link2}).replace("\n","").strip())
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
            return req.getTAL("objtypes/workflow.html", {"page":"node?id="+self.id+"&obj="+node.id, "from":xfrom, "to":to, "text":text, "subject":subject}, macro="sendmail")

    def metaFields(self):
        ret = list()
        field = tree.Node("from", "metafield")
        field.set("label", "Absender")
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("email", "metafield")
        field.set("label", "Email")
        field.set("type", "text")
        ret.append(field)
        
        field = tree.Node("subject", "metafield")
        field.set("label", "Betreff")
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("text", "metafield")
        field.set("label", "Text")
        field.set("type", "memo")
        ret.append(field)

        field = tree.Node("allowedit", "metafield")
        field.set("label", "Text Editierbar?")
        field.set("type", "list")
        field.set("valuelist", "Ja;Nein")
        ret.append(field)

        return ret
                

def mkfilelist(node, deletebutton=0, language=None, request=None):
    return request.getTAL("objtypes/workflow.html", {"files":node.getFiles(), "node":node, "delbutton":deletebutton} , macro="workflow_filelist")
    

class WorkflowStep_ShowData(WorkflowStep):

    def show_workflow_node(self, node, req):
        
        if "gotrue" in req.params:
            return self.forwardAndShow(node, True, req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)
        
        key = req.params.get("key", req.session.get("key",""))

        prefix = self.get("prefix")
        suffix = self.get("suffix")

        masks = self.get("masks")
        if not masks:
            masklist = ["editmask"]
        else:
            masklist = masks.split(";")

        fieldmap = []
        for maskname in masklist:
            mask = getMetaType(node.type).getMask(maskname)
            fieldmap += [mask.getViewHTML([node],VIEW_HIDE_EMPTY,language=lang(req))]

        #printlink = ""
        #try:
        #    f = node.show_node_printview()
        #    printlink = """<button onClick="window.open('print?id="""+node.id+"""','printwin')">Daten drucken</button>"""
        #except:
        #    pass

        filelist = ""
        if node.getFiles():
            filelist = mkfilelist(node, request=req)

        return req.getTAL("objtypes/workflow.html", {"key": key, "filelist": filelist, "fields": fieldmap, "prefix": prefix, "suffix": suffix, "buttons": self.tableRowButtons(node)}, macro="workflow_showdata")


    def metaFields(self):
        ret = list()
        field = tree.Node("prefix", "metafield")
        field.set("label", "Text vor den Daten")
        field.set("type", "memo")
        ret.append(field)
        
        field = tree.Node("suffix", "metafield")
        field.set("label", "Text nach den Daten")
        field.set("type", "memo")
        ret.append(field)
        
        field = tree.Node("masks", "metafield")
        field.set("label", "anzuzeigende Masken (;-separiert)")
        field.set("type", "text")
        ret.append(field)
        return ret

class WorkflowStep_Protect(WorkflowStep):
    def runAction(self, node, op=""):
        node.set("key", mkKey())
        self.forward(node, True)

class WorkflowStep_Upload(WorkflowStep):
   
  
    def show_workflow_node(self, node, req):
        error = ""

        for key in req.params.keys():
            if key.startswith("delete_"):
                filename = key[7:-2]
                for file in node.getFiles():
                    if file.getName() == filename:
                        node.removeFile(file)
            
        if "file" in req.params:
            file = req.params["file"]
            del req.params["file"]
            if hasattr(file,"filename") and file.filename:
                file = fileutils.importFile(file.filename,file.tempname)
                node.addFile(file)
                if hasattr(node,"event_files_changed"):
                    node.event_files_changed()
        
        
        if "gotrue" in req.params:
            if hasattr(node,"event_files_changed"):
                node.event_files_changed()
            if len(node.getFiles())>0:
                return self.forwardAndShow(node, True, req)
            else:
                error = t(req, "no_file_transferred") 

        if "gofalse" in req.params:
            if hasattr(node,"event_files_changed"):
                node.event_files_changed()
            if len(node.getFiles())>0:
                return self.forwardAndShow(node, False, req)
            else:
                error = t(req, "no_file_transferred") 

        filelist = mkfilelist(node, 1, request=req)
        
        prefix = self.get("prefix")
        suffix = self.get("suffix")

        return req.getTAL("objtypes/workflow.html", {"obj": node.id, "id": self.id,"prefix": prefix, "suffix": suffix, "filelist": filelist, "node": node, "buttons": self.tableRowButtons(node), "error":error}, macro="workflow_upload")

    def metaFields(self):
        ret = list()
        field = tree.Node("prefix", "metafield")
        field.set("label", "Text vor dem Upload-Formular")
        field.set("type", "memo")
        ret.append(field)
        
        field = tree.Node("suffix", "metafield")
        field.set("label", "Text nach dem Upload-Formular")
        field.set("type", "memo")
        ret.append(field)
        return ret

class WorkflowStep_TextPage(WorkflowStep):
    def show_workflow_node(self, node, req):
        if "gotrue" in req.params:
            return self.forwardAndShow(node, True, req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        text = self.get("text")
        
        return req.getTALstr(""" 
                <tal:block tal:replace="raw python:text"/>
                <table>
                <tal:block tal:replace="raw python:buttons"/>
                </table>
                """, {"text":text, "buttons": self.tableRowButtons(node)})
    
    def metaFields(self):
        ret = list()
        field = tree.Node("text", "metafield")
        field.set("label", "anzuzeigender Text")
        field.set("type", "memo")
        ret.append(field)
        return ret

class WorkflowStep_Delete(WorkflowStep):
    def runAction(self, node, op=""):
        for p in node.getParents():
            try:
                p.removeChild(node)
            except tree.NoSuchNodeError:
                pass

class WorkflowStep_End(WorkflowStep):
       
    def show_workflow_node(self, node, req):
        # only for debugging
        return req.getTALstr('<h2 i18n:translate="wf_step_ready">Fertig</h2><p i18n:translate="workflow_step_ready_msg">Das Objekt <span tal:content="node" i18n:name="name"/> ist am Ende des Workflows angekommen.</p>', {"node":str(node.id)})
       
    def runAction(self, node, op=""):
        pass
        #self.removeChild(node)

def register():
    tree.registerNodeClass("workflows", Workflows)
    tree.registerNodeClass("workflow", Workflow)
    tree.registerNodeClass("workflowstep", WorkflowStep)
    tree.registerNodeClass("workflowstep-start", WorkflowStep_Start)
    registerStep("workflowstep-start")
    tree.registerNodeClass("workflowstep-end", WorkflowStep_End)
    registerStep("workflowstep-end")
    tree.registerNodeClass("workflowstep-edit", WorkflowStep_EditMetadata)
    registerStep("workflowstep-edit")
    tree.registerNodeClass("workflowstep-upload", WorkflowStep_Upload)
    registerStep("workflowstep-upload")
    tree.registerNodeClass("workflowstep-delete", WorkflowStep_Delete)
    registerStep("workflowstep-delete")
    tree.registerNodeClass("workflowstep-send_email", WorkflowStep_SendEmail)
    registerStep("workflowstep-send_email")
    tree.registerNodeClass("workflowstep-showdata", WorkflowStep_ShowData)
    tree.registerNodeClass("workflowstep-wait", WorkflowStep_ShowData)
    registerStep("workflowstep-showdata")
    registerStep("workflowstep-wait")
    tree.registerNodeClass("workflowstep-protect", WorkflowStep_Protect)
    registerStep("workflowstep-protect")
    tree.registerNodeClass("workflowstep-textpage", WorkflowStep_TextPage)
    registerStep("workflowstep-textpage")
    tree.registerNodeClass("workflowstep-publish", WorkflowStep_Publish)
    registerStep("workflowstep-publish")
