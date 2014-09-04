# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2013 Tobias Stenzel <tobias.stenzel@tum.de>

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

import math
import os.path
import StringIO
from PIL import Image, ImageDraw, ImageFont

import core.config as config
from ..workflow import getWorkflow


class WorkflowImage:
    """workflow image creator
    creates image for given workflow"""
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


def send_workflow_diagram(req):
    """ method delivers workflow image as stream """
    workflow = getWorkflow(req.params.get("wid",""))
    img = WorkflowImage(workflow.getSteps())
    req.request['Content-Type'] = 'image/png';
    req.write(img.getImage().getvalue())


