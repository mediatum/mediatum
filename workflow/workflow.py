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

import Image, ImageDraw, ImageFont
import StringIO
import traceback, sys
import random

import core.config as config
import core.tree as tree
import math
import logging

from utils.utils import *
from core.tree import nodeclasses
from core.xmlnode import getNodeXML, readNodeXML

import utils.date as date
import core.acl as acl
from schema.schema import showEditor,parseEditorData,getMetaType,VIEW_HIDE_EMPTY
from core.translation import t,lang

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
    logging.getLogger('usertracing').info("workflow run action \""+newstep.getName()+"\" (op="+str(op)+") for node "+node.id)
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

def updateWorkflowStep(workflow, oldname="", newname="", type="workflowstep", trueid="", falseid="", truelabel="", falselabel="", comment=str(""), adminstep=""):
    n = workflow.getStep(oldname)
    n.setName(newname)
    n.setTypeName(type)
    n.set("truestep", trueid)
    n.set("falsestep", falseid)
    n.set("truelabel", truelabel)
    n.set("falselabel", falselabel)
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


###############################################
# workflow image creator
# creates image for given workflow
###############################################

class WorkflowImage:
   
    def __init__(self, steplist):
        # color definition
        self.spc_backcolor = (192,192,192)  # grey for start and end step
        self.std_backcolor = (255,255,255)  # white for normal step
        self.framecolor = (75,75,75)        # box frame color
        self.errorlist = list()

        self.steplist = steplist
        self.m = [[0]*len(self.steplist) for i in range(len(self.steplist))]
        self.m[0][0] = self.getStartStep().getName()
        self.stacktrue = list()
        self.stackfalse = list()

        self.stacktrue.append(self.getStartStep())
        self.stackfalse.append(self.getStartStep())

        self.maxy = 0
        self.maxx = 0
        self.buildMatrix()

        self.XSTEP = 400
        self.XSIZE = 300
        self.YSTEP = 200
        self.YSIZE = 150

        self.FONT = os.path.join(config.basedir, "utils/font.ttf")
        self.im = Image.new("RGB", ((self.maxy+1)*self.XSTEP, (self.maxx+1)*self.YSTEP), (255, 255, 255))
        self.draw = ImageDraw.ImageDraw(self.im)
        

    #
    # find startstep in steplist
    #
    def getStartStep(self):
        followers = {}
        for step in self.steplist:
            if step.getTrueId():
                followers[step.getTrueId()] = None
            if step.getFalseId():
                followers[step.getFalseId()] = None
        for step in self.steplist:
            if step.id not in followers:
                return step
        return None # circular workflow- shouldn't happen
      

    #
    # return step out of steplist
    # parameter: id=id of object to be returned
    #
    def getObject(self, id):
        for item in self.steplist:
            if item.getName() == id:
                return item

    #
    # return matrix position of step
    #
    def getPosition(self, id, add=False):
        for i in range(len(self.m)):
            for j in range(len(self.m)):
                if str(self.m[i][j]) == str(id):
                    return i,j
        
        if add: # add node if not found in matrix
            for i in range(len(self.m)):
                if str(self.m[0][i]) == str("0"):
                    self.m[0][i] = id
                    self.errorlist.append(id)
                    return 0,i
        return 0,0

    #
    # set item in matrix
    #
    def setItem(self, parent, item, op):
        x,y = self.getPosition(parent.getName())

        # true part
        if op:
            i=0
            # test bottom position
            while str(self.m[x+i][y])!="0":
                i+=1
            x += i

        # false part
        if not op:
            i=0
            # test right and upper position
            while str(self.m[x][y+i])!="0" or str(self.m[x-i][y+i])!="0":
                if str(self.m[x][y+i]) =="0":
                    self.m[x][y+i] = "x"
                i+=1
            y += i

        self.m[x][y] = item

        if y > self.maxy:
            self.maxy = y

        if x > self.maxx:
            self.maxx = x  

    #
    # main method for creating matrix
    #
    def buildMatrix(self):
        # fill all steps in the matrix

        while len(self.stacktrue)+ len(self.stackfalse)>0:
    
            # true queue
            if len(self.stacktrue)>0:
                act_t = self.stacktrue[0]
                self.stacktrue.remove(act_t)
    
            if act_t.getTrueId() and act_t.getTrueId()!=act_t.getName():
                self.stacktrue.append(self.getObject(act_t.getTrueId()))
                if self.getPosition(act_t.getTrueId())==(0,0):
                    self.setItem(act_t, act_t.getTrueId(), True)


            if act_t.getFalseId() and act_t.getFalseId()!=act_t.getName():
                self.stackfalse.append(self.getObject(act_t.getFalseId()))
                if self.getPosition(act_t.getFalseId())==(0,0):
                    self.setItem(act_t, act_t.getFalseId(), False)

            # false queue
            if len(self.stackfalse)>0:
                act_f = self.stackfalse[0]
                self.stackfalse.remove(act_f)
    
            if act_f.getTrueId() and act_f.getTrueId()!=act_f.getName():
                if self.getPosition(act_f.getTrueId())==(0,0):
                    self.stacktrue.append(self.getObject(act_f.getTrueId()))
                    self.setItem(act_f, act_f.getTrueId(), True)

            if act_f.getFalseId() and act_f.getFalseId()!=act_f.getName():
                self.stackfalse.append(self.getObject(act_f.getFalseId()))
                if self.getPosition(act_f.getFalseId())==(0,0):
                    self.setItem(act_f, act_f.getFalseId(), False)
        
        # matrix reformatation
        for i in range(self.maxx+1):
            for j in range(self.maxy+1):
                if self.m[i][j] =="x":
                    self.m[i][j] ="0"
   
    """ format matrix for debug purposes only """
    def output(self):
        line = ""
        for i in range(self.maxx+1):
            for j in range(self.maxy+1):
                line += str(self.m[i][j]) + "  "
            line = ""

    """ draw each step and return image (png) """
    def getImage(self):
        for step in list(self.steplist):
            self.drawStep(step)

        del self.draw
        f = StringIO.StringIO()
        self.im.save(f, "PNG")
        return f

    """ calculate angel of vector for arrow usage """
    def calculateAngle(self, p1x,p1y, p2x,p2y):
        return math.atan2( p2x-p1x, p2y-p1y)
    
    def getPoint(self, angle, x, fix):
        #angle = math.radians(angle)
        x1 = fix[0] + (x[0]-fix[0])*math.cos(angle) + (x[1]-fix[1])*math.sin(angle)
        y1 = fix[1] + (x[0]-fix[0])*math.sin(angle) - (x[1]-fix[1])*math.cos(angle)
        return round(y1), round(x1)
 
    """ draws the connection of two 2given steps
        parameter: f=coordinates from, t=coordinates to, col=color """
    def drawArrow(self, f=(0,0), t=(0,0), text="", type="true"):

        if type=="true":
            corr = -10                                  # correction parameter
            col = (0,128,0)                             # color
        else:
            corr = +10                                  # correction parameter
            col = (255,0,0)                             # color
  
        l1 = f[1] * self.XSTEP                          # left position of box (start)
        t1 = f[0] * self.YSTEP                          # top position of box (start)
        s1l = (l1,t1+(self.YSIZE/2)+corr)               # step 1 left
        s1t = (l1+(self.XSIZE/2)+corr,t1)               # step 1 top
        s1r = (l1+(self.XSIZE),t1+(self.YSIZE/2)+corr)  # step 1 right
        s1b = (l1+(self.XSIZE/2)+corr,t1+(self.YSIZE))  # step 1 bottom

        l2 = t[1] * self.XSTEP                          # left posisition of box (end)
        t2 = t[0] * self.YSTEP                          # top position of box (start)
        s2l = (l2,t2+(self.YSIZE/2)+corr)               # step 2 left
        s2t = (l2+(self.XSIZE/2)+corr,t2)               # step 2 top
        s2r = (l2+(self.XSIZE),t2+(self.YSIZE/2)+corr)  # step 2 right
        s2b = (l2+(self.XSIZE/2)+corr,t2+(self.YSIZE))  # step 2 bottom
        
        angle = self.calculateAngle(l1,t1, l2,t2)

        if l1==l2: # vertical
            if t1<t2:   # down
                pf = (s1b[0],s1b[1])
                pt = (s2t[0],s2t[1])

            else:       # up
                pf = (s1t[0],s1t[1])
                pt = (s2b[0],s2b[1])

        if t1==t2: # horizontal
            if l1<l2:   # right
                pf = (s1r[0],s1r[1])
                pt = (s2l[0],s2l[1])

            else:       # left
                pf = (s1l[0],s1l[1])
                pt = (s2r[0],s2r[1])
                
        if t1!=t2 and l1!=l2: # diagonal

            if l1<l2:   # left -> right
                if t1<t2:     # down 
                    pf = (s1r[0],s1r[1])
                    pt = (s2t[0],s2t[1])
      
                else:         # up
                    pf = (s1t[0],s1t[1])
                    pt = (s2b[0],s2b[1])

            else:       # right -> left
                if t1<t2:     # down 
                    pf = (s1l[0],s1l[1])
                    pt = (s2t[0],s2t[1])

                else:         # up
                    pf = (s1l[0],s1l[1])
                    pt = (s2b[0],s2b[1])
        
        self.draw.line((pf[0],pf[1], pt[0],pt[1]), fill=col)
        self.draw.polygon((self.getPoint(angle,(pt[1],pt[0]),(pt[1],pt[0]) ), 
                           self.getPoint(angle,(pt[1]-5,pt[0]-6),(pt[1],pt[0])), 
                           self.getPoint(angle,(pt[1]-5,pt[0]+5),(pt[1],pt[0]))), 
                           fill=col)
 

    """ print step in context """
    def drawStep(self, step):
        x,y = self.getPosition(step.getName(), True)

        color = self.std_backcolor
        #if step.isStart() or step.isEnd():
        #    color = self.spc_backcolor

        if step.getName() in self.errorlist:
            color = self.spc_backcolor
       
        name = unicode(step.getName(),"utf-8").encode("latin-1","replace")
        comment = unicode(step.getComment(),"utf-8").encode("latin-1","replace")
        labeltrue = unicode(step.getTrueLabel(),"utf-8").encode("latin-1","replace")
        labelfalse = unicode(step.getFalseLabel(),"utf-8").encode("latin-1","replace")
        #w, h, i = self.setFontSize(name)
        i = self.XSIZE/30
        i2 = self.XSIZE/30 + 2
        self.draw.setfont(ImageFont.truetype(self.FONT, i2))
        w,h = self.draw.textsize(name)
        
        # true
        if step.getTrueId() and (step.getName() not in self.errorlist):
            self.drawArrow((x,y), self.getPosition(step.getTrueId()), labeltrue, "true")

        # false
        if step.getFalseId() and (step.getName() not in self.errorlist):
            self.drawArrow((x,y), self.getPosition(step.getFalseId()), labelfalse, "false")
       
        self.draw.setfont(ImageFont.truetype(self.FONT, i))
        self.draw.rectangle(((y*self.XSTEP), (x*self.YSTEP), (y*self.XSTEP)+self.XSIZE, (x*self.YSTEP)+self.YSIZE), self.framecolor)
        self.draw.rectangle(((y*self.XSTEP)+2, (x*self.YSTEP)+2, (y*self.XSTEP)+self.XSIZE-2, (x*self.YSTEP)+self.YSIZE-2), color)
        self.drawtextbox(y*self.XSTEP+5, x*self.YSTEP + i*4, self.XSIZE-10, self.YSIZE - i*4, comment, (0,0,0))
        self.draw.text((((y*self.XSTEP)+(self.XSIZE-w)/2), ((x * self.YSTEP)+h/2)) , name, fill=(0,0,0))

    def parsetext(self,text):
        tokens = []
        pos = 0
        while pos < len(text):
            oldpos = pos
            while pos < len(text) and text[pos] not in " -/\t\r\n":
                pos = pos + 1
            word = text[oldpos:pos]
            token = pos < len(text) and text[pos] or " "
            if token in "-/":
                word += token
                token = ''
                pos = pos+1
            if token == '\r':
                token = '\n'
            if token == '\t':
                token = ' '
            if word:
                tokens += [(word,token)]
            while pos < len(text) and text[pos] in " \t\r\n":
                pos = pos+1
        return tokens

    def drawtextbox(self,xx,yy,width,height,text,color):
        dummy,leading = self.draw.textsize(text)
        space,dummy = self.draw.textsize(" ")
        x,y = 0,0
        for word, token in self.parsetext(text):
            w,h = self.draw.textsize(word)
            if x+w > width:
                y += leading
                x = 0
            self.draw.text((x+xx,y+yy), word, fill=color)
            x += w
            if token == '\n':
                y += leading
                x = 0
            elif token == " ":
                x += space
    
    #
    # evalutate correct font size
    #
    #def setFontSize(self, text):
    #    i=w=h=1
    #    if len(text)<10:
    #        length = 45
    #    else:
    #        length = 90        

    #    while w < length:
    #        self.draw.setfont(ImageFont.truetype(self.FONT, i))
    #        w,h = self.draw.textsize(text)
    #        i+=1
    #    return w, h, i



""" method delivers workflow image as stream """
def createWorkflowImage(req):
    workflow = getWorkflow(req.params.get("wid",""))
    img = WorkflowImage(workflow.getSteps())
    req.request['Content-Type'] = 'image/png';
    req.write(img.getImage().getvalue())

          
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
        w.setName("import-"+w.getName())
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
                    
                    return self.show_workflow_node(node, req)
                    #if "raw" in req.params:
                    #    return self.show_workflow_node(node, req)
                    #else:
                    #    return self.show_workflow_node(node, req)
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
        return req.getTAL("workflow/workflow.html", {"node": node, "name":self.name}, macro="workflow_node")
     

    def show_workflow_step(self, req):
        access = acl.AccessData(req)
        if not access.hasWriteAccess(self):
            return '<i>'+t(lang(req),"permission_denied")+'</i>'
        
        c = []
        for item in self.getChildren():
            c.append({"id":str(item.id), "creationtime":date.format_date(date.parse_date(item.get('creationtime')),'dd.mm.yyyy HH:MM:SS'), "name": item.getName()})
        c.sort(lambda x, y: cmp(x['name'], y['name']))

        return req.getTAL("workflow/workflow.html", {"children":c, "workflow":self.getParents()[0], "step": self, "nodelink": "/mask?id="+self.id+"&obj="}, macro="workflow_show")
    
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
        return runWorkflowStep(node, op)
   
    def forwardAndShow(self, node, op, req, link=None):
        newnode = self.forward(node, op)

        if newnode is None:
            return req.getTAL("workflow/workflow.html", {"node":node}, macro="workflow_forward")

        if link is None:
            newloc = req.makeLink("/mask", {"id":newnode.id, "obj":node.id})
        else:
            newloc = link
        redirect = 1
        if redirect == 0:
            return req.getTAL("workflow/workflow.html", {"newnodename":newnode.name, "email":config.get("email.workflow")}, macro="workflow_forward2")
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

    def metaFields(self, lang=None):
        return list()

    def tableRowButtons(self, node):
        result = '<table id="workflowbuttons"><tr><td align="left">'
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
        result += '</td></tr></table>'
        return result
        
    def getTypeName(self):
        return self.getName()

def register():
    tree.registerNodeClass("workflows", Workflows)
    tree.registerNodeClass("workflow", Workflow)
    tree.registerNodeClass("workflowstep", WorkflowStep)
    from start import WorkflowStep_Start
    tree.registerNodeClass("workflowstep-start", WorkflowStep_Start)
    registerStep("workflowstep-start")
    from end import WorkflowStep_End
    tree.registerNodeClass("workflowstep-end", WorkflowStep_End)
    registerStep("workflowstep-end")
    from editmetadata import WorkflowStep_EditMetadata
    tree.registerNodeClass("workflowstep-edit", WorkflowStep_EditMetadata)
    registerStep("workflowstep-edit")
    from upload import WorkflowStep_Upload
    tree.registerNodeClass("workflowstep-upload", WorkflowStep_Upload)
    registerStep("workflowstep-upload")
    from delete import WorkflowStep_Delete
    tree.registerNodeClass("workflowstep-delete", WorkflowStep_Delete)
    registerStep("workflowstep-delete")
    from email import WorkflowStep_SendEmail
    tree.registerNodeClass("workflowstep-send_email", WorkflowStep_SendEmail)
    registerStep("workflowstep-send_email")
    from showdata import WorkflowStep_ShowData
    tree.registerNodeClass("workflowstep-showdata", WorkflowStep_ShowData)
    tree.registerNodeClass("workflowstep-wait", WorkflowStep_ShowData)
    registerStep("workflowstep-showdata")
    registerStep("workflowstep-wait")
    from protect import WorkflowStep_Protect
    tree.registerNodeClass("workflowstep-protect", WorkflowStep_Protect)
    registerStep("workflowstep-protect")
    from textpage import WorkflowStep_TextPage
    tree.registerNodeClass("workflowstep-textpage", WorkflowStep_TextPage)
    registerStep("workflowstep-textpage")
    from publish import WorkflowStep_Publish
    tree.registerNodeClass("workflowstep-publish", WorkflowStep_Publish)
    registerStep("workflowstep-publish")
