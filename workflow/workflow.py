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

import os
import Image, ImageDraw, ImageFont
import StringIO
import traceback, sys
import random
import pkgutil
import importlib

import core.config as config
import core.tree as tree
import core.athana as athana
import math
import logging

from utils.utils import *
from core.tree import nodeclasses
from core.xmlnode import getNodeXML, readNodeXML

import utils.date as date
import core.acl as acl
from schema.schema import showEditor,parseEditorData,getMetaType,VIEW_HIDE_EMPTY
from core.translation import t, lang, addLabels, getDefaultLanguage, switch_language
from core.users import getUserFromRequest, getUser

import thread

import utils.fileutils as fileutils

log = logging.getLogger('backend')


def getWorkflowList():
    return tree.getRoot("workflows").getChildren()

def getWorkflow(name):
    if name.isdigit():
        return tree.getNode(name)
    else:
        return tree.getRoot("workflows").getChild(name)

def addWorkflow(name,description):
    node = tree.getRoot("workflows").addChild(tree.Node(name=name, type="workflow"))
    node.set("description",description)

def updateWorkflow(name,description,origname="", writeaccess=""):
    if origname=="":
        node = tree.getRoot("workflows")
        if not node.hasChild(name):
            addWorkflow(name, description)
        w = tree.getRoot("workflows").getChild(name)
    else:
        w = tree.getRoot("workflows").getChild(origname)
        w.setName(name)
    w.set("description", description)
    w.setAccess("write", writeaccess)

def deleteWorkflow(id):
    workflows = tree.getRoot("workflows")
    w = workflows.getChild(id)
    workflows.removeChild(w)

def inheritWorkflowRights(name, type):
    w = getWorkflow(name)
    ac = w.getAccess(type)
    for step in w.getChildren():
        step.setAccess(type, ac)


def getNodeWorkflow(node):
    for p in node.getParents():
        for p2 in p.getParents():
            if p2.type == "workflow":
                return p2
    return None

def getNodeWorkflowStep(node):
    workflow = getNodeWorkflow(node)
    if workflow is None:
        return None
    steps = [n.id for n in workflow.getSteps()]
    for p in node.getParents():
        if p.id in steps:
            return p
    return None

# execute step operation and set node step
def runWorkflowStep(node, op):
    workflow = getNodeWorkflow(node)
    workflowstep = getNodeWorkflowStep(node)

    if workflowstep is None:
        return

    newstep = None
    if op == "true":
        newstep = workflow.getStep(workflowstep.getTrueId())
    else:
        newstep = workflow.getStep(workflowstep.getFalseId())

    workflowstep.removeChild(node)
    newstep.addChild(node)
    newstep.runAction(node, op)
    #logging.getLogger('usertracing').info("workflow run action \""+newstep.getName()+"\" (op="+str(op)+") for node "+node.id)
    log.info('workflow run action "%s" (op="%s") for node %s' %(newstep.getName(), op, node.id))
    return getNodeWorkflowStep(node)

# set workflow for node
def setNodeWorkflow(node,workflow):
    start = workflow.getStartNode()
    start.addChild(node)
    start.runAction(node, True)
    return getNodeWorkflowStep(node)

def createWorkflowStep(name="", type="workflowstep", trueid="", falseid="", truelabel="", falselabel="", comment=str(""), adminstep=""):
    n = tree.Node(name=name, type=type)
    n.set("truestep", trueid)
    n.set("falsestep", falseid)
    n.set("truelabel", truelabel)
    n.set("falselabel", falselabel)
    n.set("comment", comment)
    n.set("adminstep", adminstep)
    return n

def updateWorkflowStep(workflow, oldname="", newname="", type="workflowstep", trueid="", falseid="", truelabel="", falselabel="", sidebartext='', pretext="", posttext="", comment='', adminstep=""):
    n = workflow.getStep(oldname)
    n.setName(newname)
    n.setTypeName(type)
    n.set("truestep", trueid)
    n.set("falsestep", falseid)
    n.set("truelabel", truelabel)
    n.set("falselabel", falselabel)
    n.set("sidebartext", sidebartext)
    n.set("pretext", pretext)
    n.set("posttext", posttext)
    n.set("comment", comment)
    n.set("adminstep", adminstep)
    for node in workflow.getChildren():
        if node.get("truestep") == oldname:
            node.set("truestep", newname)
        if node.get("falsestep") == oldname:
            node.set("falsestep", newname)
    return n

def deleteWorkflowStep(workflowid, stepid):
    workflows = tree.getRoot("workflows")
    wf = workflows.getChild(workflowid)
    ws = wf.getChild(stepid)
    wf.removeChild(ws)

workflowtypes = {}

def registerStep(nodename):
    name = nodename
    if "-" in nodename:
        name = nodename[nodename.index("-")+1:]
    workflowtypes[nodename] = name

def registerWorkflowStep(nodename, cls):
    name = nodename
    if "-" in nodename:
        name = nodename[nodename.index("-")+1:]
    workflowtypes[nodename] = name

    addLabels(cls.getLabels())




def getWorkflowTypes():
    return workflowtypes


def workflowSearch(nodes, text, access=None):
    text = text.strip()
    if text=="":
        return []

    ret = []
    for node in filter(lambda x: x.getContentType()=='workflow', nodes):
        for n in node.getSteps(access, "write"):
            for c in n.getChildren():
                if text=="*":
                    ret += [c]
                elif isNumeric(text):
                    if c.id==text:
                        ret +=[c]
                else:
                    if "|".join([f[1].lower() for f in c.items()]).find(text.lower())>=0:
                        ret += [c]

    return ret

def formatItemDate(d):
    try:
        return date.format_date(date.parse_date(d),'dd.mm.yyyy HH:MM:SS')
    except:
        return ""


""" export workflow definition """
def exportWorkflow(name):
    if name=="all":
        return getNodeXML(tree.getRoot("workflows"))
    else:
        return getNodeXML(getWorkflow(name))


""" import workflow from file """
def importWorkflow(filename):
    n = readNodeXML(filename)
    importlist = list()

    if n.getContentType() == "workflow":
        importlist.append(n)
    elif n.getContentType()=="workflows":
        for ch in n.getChildren():
            importlist.append(ch)
    workflows = tree.getRoot("workflows")
    for w in importlist:
        w.setName("import-" + w.getName())
        workflows.addChild(w)

class Workflows(tree.Node):
    def show_node_big(node, req, template="workflow/workflow.html", macro="workflowlist"):
        access = acl.AccessData(req)

        list = []
        for workflow in getWorkflowList():
            if access.hasWriteAccess(workflow):
                list += [workflow]
        return req.getTAL(template, {"list":list, "search":req.params.get("workflow_search", ""), "items":workflowSearch(list, req.params.get("workflow_search", ""), access),"getStep": getNodeWorkflowStep,"format_date": formatItemDate}, macro=macro)

    def isContainer(node):
        return 1

    def isSystemType(node):
        return 1

    def getLabel(node):
        return node.name


class Workflow(tree.Node):
    def show_node_big(node, req, template="workflow/workflow.html", macro="object_list"):
        access = acl.AccessData(req)
        if not access.hasWriteAccess(node):
            return '<i>' + t(lang(req),"permission_denied") + '</i>'
        return req.getTAL(template, {"workflow": node, "access":access, "search":req.params.get("workflow_search", ""), "items":workflowSearch([node], req.params.get("workflow_search", ""), access),"getStep": getNodeWorkflowStep,"format_date": formatItemDate}, macro=macro)

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

    def isContainer(node):
        return 1

    def isSystemType(node):
        return 1

    def getLanguages(node):
        if node.get('languages')!='':
            return node.get('languages').split(';')
        return []

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

    def getSteps(self, access=None, accesstype="read"):
        steps = self.getChildren()
        if access:
            return access.filter(steps, accesstype=accesstype)
        else:
            return steps

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
        if name.isdigit():
            return tree.getNode(name)
        else:
            return self.getChild(name)

    def getNodeList(self):
        list = []
        for step in self.getSteps():
            list += step.getChildren()
        return list

    def addStep(self,step):
        self.addChild(step)
        return step


workflow_lock = thread.allocate_lock()

class WorkflowStep(tree.Node):

    def getId(self):
        return self.getName()

    def show_node_big(self, req, template="workflow/workflow.html", macro="object_step"):

        # the workflow operations (node forwarding, key assignment,
        # parent node handling) are highly non-reentrant, so protect
        # everything with a global lock
        global workflow_lock
        workflow_lock.acquire()

        try:
            access = acl.AccessData(req)
            if "obj" in req.params:
                node = tree.getNode(req.params["obj"])
                key = req.params.get("key", req.session.get("key", ""))
                req.session["key"] = key

                if not access.hasWriteAccess(self) and \
                    (key != node.get("key")): # no permission

                    link = '('+self.name+')'
                    try:
                        return req.getTAL(template, {"node": node, "link":link, "email":config.get("email.workflow")}, macro=macro)
                    except:
                        return ""

                if self in node.getParents():
                    # set correct language for workflow for guest user only
                    if node.get('key')==node.get('system.key') and getUserFromRequest(req)==getUser(config.get('user.guestuser')):
                        switch_language(req, node.get('system.wflanguage'))

                    link = req.makeLink("/mask", {"id":self.id})
                    if "forcetrue" in req.params:
                        return self.forwardAndShow(node, True, req, link=link)
                    if "forcefalse" in req.params:
                        return self.forwardAndShow(node, False, req, link=link)

                    return self.show_workflow_node(node, req)
                else:
                    return self.show_workflow_notexist(node, req)
            else:
                return self.show_workflow_step(req)

        finally:
            workflow_lock.release()

    def isContainer(self):
        # inhibit several content enrichment features
        return 1

    def isSystemType(self):
        return 1

    def show_workflow_notexist(self, node, req, template="workflow/workflow.html", macro="workflow_node"):
        step = getNodeWorkflowStep(node)
        link = ""
        if step:
            link = '/mask?id=%s&obj=%s' % (step.id,node.id)
            return '<script language="javascript">document.location.href = "%s";</script> <a href="%s">%s</a>' % (link, link, step.name)
        else:
            return '<i>%s</i>' %(t(lang(req), "permission_denied"))


    def show_workflow_node(self, node, req):

        if "gotrue" in req.params:
            return self.forwardAndShow(node, True, req)
        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        # to be overloaded
        return req.getTAL("workflow/workflow.html", {"node": node, "name":self.name}, macro="workflow_node")


    def show_workflow_step(self, req):
        access = acl.AccessData(req)
        if not access.hasWriteAccess(self):
            return '<i>'+t(lang(req),"permission_denied")+'</i>'
        c = []
        for item in self.getChildren():
            c.append({"id":str(item.id), "creationtime":date.format_date(date.parse_date(item.get('creationtime')),'dd.mm.yyyy HH:MM:SS'), "name": item.getName()})
        c.sort(lambda x, y: cmp(x['name'], y['name']))
        return req.getTAL("workflow/workflow.html", {"children":c, "workflow":self.getParents()[0], "step": self, "nodelink": "/mask?id="+self.id+"&obj=", 'currentlang':lang(req)}, macro="workflow_show")

    def show_node_image(node):
        return '<img border="0" src="/img/directory.png">'

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
        if self.getTrueId()=='': # no next step defined
            log.error("No Workflow action defined for workflowstep "+self.getId()+" (op="+str(op)+")")

    def forward(self, node, op):
        if op==True:
            op = "true"
        elif op==False:
            op = "false"
        return runWorkflowStep(node, op)

    def forwardAndShow(self, node, op, req, link=None, data=None):
        newnode = self.forward(node, op)

        if newnode is None:
            return req.getTAL("workflow/workflow.html", {"node":node}, macro="workflow_forward")

        if link is None:
            context = {"id":newnode.id, "obj":node.id}
            if data and type(data)==type({}):
               for k in data:
                   if not k in context:
                       context[k] = data[k]
                   else:
                       msg_t = (getNodeWorkflow(node).name, getNodeWorkflowStep(node).name, node.id, k, data[k])
                       log.warning("workflow '%s', step '%s', node %s: ignored data key '%s' (value='%s')" % msg_t)

            newloc = req.makeLink("/mask", context)
        else:
            newloc = link
        redirect = 1
        if redirect==0:
            return req.getTAL("workflow/workflow.html", {"newnodename":newnode.name, "email":config.get("email.workflow")}, macro="workflow_forward2")
        else:
            if config.get("config.ssh", "")=="yes":
                if not newloc.lower().startswith("https:"):
                    newloc = "https://"+config.get("host.name") + newloc.replace("http://"+config.get("host.name"), "")
            return '<script language="javascript">document.location.href = "%s";</script>' % newloc

    def getTrueId(self):
        return self.get("truestep")

    def getFalseId(self):
        return self.get("falsestep")

    def getTrueLabel(self, language=""):
        value = self.get("truelabel")
        for line in value.split('\n'):
            if line.startswith(language+':'):
                return line.replace(language+':', '')
        value = value.split('\n')[0] # use first language
        for lang in config.get('i18n.languages').split(','):
            value = value.replace('%s:' %(lang), '')
        return value.strip()

    def getFalseLabel(self, language=""):
        value = self.get("falselabel")
        for line in value.split('\n'):
            if line.startswith(language+':'):
                return line.replace(language+':', '')
        value = value.split('\n')[0] # use first language
        for lang in config.get('i18n.languages').split(','):
            value = value.replace('%s:' %(lang), '')
        return value.strip()

    def getTrueFunction(self):
        return self.get("truefunction")

    def getFalseFunction(self):
        return self.get("falsefunction")

    def getSidebarText(self, language=""):
        value = self.get("sidebartext")
        for line in value.split('\n'):
            if line.startswith(language+':'):
                return line.replace(language+':', '')
        return value

    def getPreText(self, language=""):
        value = self.get("pretext")
        for line in value.split('\n'):
            if line.startswith(language+':'):
                return line.replace(language+':', '')
        return value

    def getPostText(self, language=""):
        value = self.get("posttext")
        for line in value.split('\n'):
            if line.startswith(language+':'):
                return line.replace(language+':', '')
        return value

    def getComment(self):
        return self.get("comment")

    def metaFields(self, lang=None):
        return list()

    def tableRowButtons(self, node):
        if node.get('system.key')==node.get('key'):
            # user has permission -> use users language
            return athana.getTAL("workflow/workflow.html", {'node':node, 'wfstep':self, 'lang':node.get('system.wflanguage')}, macro="workflow_buttons", language=node.get('system.wflanguage'))
        else:
            # use standard language of request
            return athana.getTAL("workflow/workflow.html", {'node':node, 'wfstep':self, 'lang':getDefaultLanguage()}, macro="workflow_buttons", language=getDefaultLanguage())


    def getTypeName(self):
        return self.getName()

    def getShortName(self, req):
        l = lang(req)
        if self.get('shortstepname_'+l)!="":
            return self.get('shortstepname_'+l)
        elif self.get('shortstepname')!="":
            return self.get('shortstepname')
        else:
            return ""

    def setShortName(self, value, lang=""):
        if lang!="":
            self.set('shortstepname_'+lang, value.strip())
        else:
            self.set('shortstepname', value.strip())


def register():
    tree.registerNodeClass("workflows", Workflows)
    tree.registerNodeClass("workflow", Workflow)
    tree.registerNodeClass("workflowstep", WorkflowStep)

    # run register method of step types
    path = os.path.dirname(__file__)
    for _, name, _ in pkgutil.iter_modules([path]):
        if name != "workflow":
            m = importlib.import_module("workflow." + name)
            if hasattr(m, 'register'):
                log.info("registering workflow step '%s'", name)
                m.register()
