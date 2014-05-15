"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>

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
import Image
import core.config as config
import core.tree as tree
import core.acl as acl
import core.users as users

from core.stats import buildStat, StatisticFile
from core.translation import t, lang
from utils.utils import splitpath
from utils.date import format_date, now

try:
    from reportlab.platypus import Paragraph, XPreformatted, BaseDocTemplate, SimpleDocTemplate, FrameBreak, Table, TableStyle, Image as PdfImage,Frame,PageBreak,PageTemplate
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.rl_config import defaultPageSize
    from reportlab.pdfgen import canvas
    reportlab=1
except:
    reportlab=0

def getPeriod(filename):
    filename = splitpath(filename)[-1]
    period = filename[:-4].split("_")[2]
    type = filename[:-4].split("_")[3]
    return period, type


def getContent(req, ids):
    if len(ids)>0:
        ids = ids[0]

    user = users.getUserFromRequest(req)
    node = tree.getNode(ids)
    access = acl.AccessData(req)
    
    if "statsaccess" in users.getHideMenusForUser(user) or  not access.hasWriteAccess(node):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if req.params.get("style", "")=="popup":
        getPopupWindow(req, ids)
        return ""

    node = tree.getNode(ids)
    statfiles = {}
    p = ""
    
    for file in node.getFiles():
        if file.getType()=="statistic":
            period, type = getPeriod(file.retrieveFile())
            if period>p:
                p = period
            
            if type not in statfiles.keys():
                statfiles[type] = {}
            
            if period not in statfiles[type].keys():
                statfiles[type][period] = []
            statfiles[type][period].append(file)

    v = {}
    v["id"] = ids
    v["files"] = statfiles
    v["current_period"] = req.params.get("select_period", "frontend_" + p)
    if len(statfiles)>0:
        v["current_file"] = StatisticFile(statfiles[v["current_period"].split("_")[0]][v["current_period"].split("_")[1]][0])
    else:
        v["current_file"] = StatisticFile(None)
    v["nodename"] = tree.getNode

    items = v["current_file"].getProgress('country')
    return req.getTAL("web/edit/modules/statsaccess.html", v, macro="edit_stats")

    
def getPopupWindow(req, ids):
    v = {}
    v["id"] = ids
    if "update" in req.params:
        v["action"] = "doupdate"
    
    elif req.params.get("action")=="do": # do action and refresh current month
        collection = tree.getNode(req.params.get("id"))
        collection.set("system.statsrun", "1")
        buildStat(collection, str(format_date(now(), "yyyy-mm")))
        req.writeTAL("web/edit/modules/statsaccess.html", {}, macro="edit_stats_result")
        collection.removeAttribute("system.statsrun")
        return
        
    else:
        v["action"] = "showform"
        v["statsrun"] = tree.getNode(ids).get("system.statsrun")
    req.writeTAL("web/edit/modules/statsaccess.html", v, macro="edit_stats_popup")

    
class StatsAccessPDF:

    def __init__(self, data, period, id, language):
        self.styleSheet = getSampleStyleSheet()
        self.stats = data
        self.period = period
        self.language = language
        self._pages = 1
        self.data = []
        self.collection = tree.getNode(id)
        
        
    def myPages(self, canvas, doc):
        doc.pageTemplate.frames = self.getStyle(self._pages)
        canvas.saveState()
        canvas.setFont('Helvetica',8)
        canvas.restoreState()
        self._pages += 1
        
    
    def getStyle(self, page):
        frames = []
        
        if page==1: # first page
            frames.append(Frame(1*cm, 25.5*cm, 19*cm, 3*cm,leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # main header
            # top 10
            frames += self.getStatTop("frames")

        elif page==2: # page 2
            frames.append(Frame(1*cm, 27.5*cm, 19*cm, 1*cm,leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # main header pages >1
            # countries
            frames += self.getStatCountry("frames")
        
        elif page==3: # page 3
            frames.append(Frame(1*cm, 27.5*cm, 19*cm, 1*cm,leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # main header pages >1
            # date
            frames += self.getStatDate("frames")
            
        elif page==4: # page 4
            frames.append(Frame(1*cm, 27.5*cm, 19*cm, 1*cm,leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # main header pages >1
            # weekday
            frames += self.getStatDay("frames")
            
            # time
            frames += self.getStatTime("frames")
            
        return frames

        
    def getStatTop(self, type, namecut=0):
        # frames
        items = []
        d = self.stats.getIDs()
        max = float(d[0][1])
        if max==0:
            max+=1
        if type=="frames":
            items.append(Frame(1*cm, 24.0*cm, 19*cm, 1*cm,leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # header
            for i in range(0, 45):
                if i<len(d):
                    items.append( Frame(1*cm, (22.9-(i*0.5))*cm, 8*cm, 25, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # label
                    items.append( Frame(9*cm, (23.0-(i*0.5))*cm, d[i][1]*280/max, 25, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # bar
                    items.append( Frame(9*cm+(d[i][1]*280/max)+5, (22.9-(i*0.5))*cm, 40, 25, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # number
            
        # data
        if type=="data":
            items.append(Paragraph(t(self.language, "edit_stats_access"), self.chartheader))
            items.append((FrameBreak()))

            for i in range(0, 45):
                if i<len(d):
                    try:
                        nodename = tree.getNode(d[i][0]).getName()
                        suffix = " (" + str(d[i][0])+")"
                        n = nodename + suffix
                        if namecut > 0 and len(n) > namecut:
                            delta = len(n)-namecut
                            new_length = len(nodename)-delta-3
                            n = nodename[0:new_length] + "..." + suffix
                    except:
                        n = str(d[i][0])
                    items.append( Paragraph(n, self.bv))
                    items.append((FrameBreak()))
                    items.append(PdfImage(config.basedir+"/web/img/stat_bar.png", width=d[i][1]*280/max, height=10))
                    items.append((FrameBreak()))
                    items.append( Paragraph(str(d[i][1]), self.bv))
                    items.append((FrameBreak()))
        return items
        
        
    def getStatCountry(self, type):
        items = []
        d = self.stats.getProgress('country')
        max = float(d[0]["max"])
        
        if type=="frames":
            items.append(Frame(1*cm, 26.0*cm, 19*cm, 1*cm, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # header country
            i = 0
            for v in sorted([(len(d[k]['items']), k) for k in filter(lambda x:x!=0, d.keys())], reverse=True):
                if v[0]!=0:
                    items.append( Frame(1*cm, (25.1-(i*0.5))*cm, 3*cm, 25, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # label
                    items.append( Frame(4*cm, (25.2-(i*0.5))*cm, v[0]*400/max, 25, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # bar
                    items.append( Frame(4*cm+(v[0]*400/max)+5, (25.1-(i*0.5))*cm, 40, 25, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # number
                    i += 1
        
        if type=="data":
            items.append(Paragraph(t(self.language, "edit_stats_country"), self.chartheader))
            items.append((FrameBreak()))

            for v in sorted([(len(d[k]['items']), k) for k in filter(lambda x:x!=0, d.keys())], reverse=True)[:50]:
                if v[0]!=0:
                    items.append( Paragraph(str(v[1]), self.bv))
                    items.append((FrameBreak()))
                    items.append(PdfImage(config.basedir+"/web/img/stat_bar.png", width=v[0]*400/max, height=10))
                    items.append((FrameBreak()))
                    items.append( Paragraph(str(v[0]), self.bv))
                    items.append((FrameBreak()))
            
            items = items[:-1]
        return items
            
    def getStatDate(self, type):
        items = []
        d = self.stats.getProgress()
        max = d[0]
        
        if type=="frames":
            items.append(Frame(1*cm, 26.0*cm, 19*cm, 1*cm, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # header date
            x = (32-len(d))*8 # add left space if month with less than 31 days

            for k in d:
                if k==0:
                   continue
                items.append(Frame(1*cm+(k-1)*17+9+x, 18.9*cm, 5, len(d[k]["visitors"])*(6*cm)/max["max_u"]+16, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # col 1
                items.append(Frame(1*cm+(k-1)*17+14+x, 18.9*cm, 5, len(d[k]["different"])*(6*cm)/max["max_p"]+16, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # col 2
                items.append(Frame(1*cm+(k-1)*17+19+x, 18.9*cm, 5, len(d[k]["items"])*(6*cm)/max["max"]+16, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # col 3

            items.append(Frame(1*cm, 17.8*cm, 19*cm, 1.5*cm,leftPadding=4, rightPadding=0, id='normal', showBoundary=0)) # legend table with days
            items.append(Frame(1*cm, 1*cm, 19*cm, 16*cm,leftPadding=4, rightPadding=0, id='normal', showBoundary=0)) # table with values  
    
        if type=="data":
            items.append(Paragraph(t(self.language,"edit_stats_spreading"), self.chartheader))
            items.append(FrameBreak())

            for k in d:
                if k==0:
                   continue
                items.append(PdfImage(config.basedir+"/web/img/stat_baruser_vert.png", width=5, height=((len(d[k]["visitors"])*(6*cm)/max["max_u"]+1) or 1)))
                items.append(FrameBreak())
                items.append(PdfImage(config.basedir+"/web/img/stat_barpage_vert.png", width=5, height=((len(d[k]["different"])*(6*cm)/max["max_p"]+1) or 1)))
                items.append(FrameBreak())
                items.append(PdfImage(config.basedir+"/web/img/stat_bar_vert.gif", width=5, height=((len(d[k]["items"])*(6*cm)/max["max"]+1) or 1)))
                items.append(FrameBreak())

            t_data = []
            weekend = []
            for k in d:
                if k>0: # first item holds max values
                    if self.stats.getWeekDay(k)>4:
                        weekend.append(('BACKGROUND', (k-1,0), (k-1,-1), colors.HexColor('#E6E6E6')))
                    t_data.append('%02d \n%s' %(k, t(self.language, "monthname_"+str(int(self.period[-2:]))+"_short")))

            tb = Table([t_data], 31*[17], 30)
            tb.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('ALIGN',(0,0), (-1,-1), 'CENTER'),
                    ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
                    ('BOX', (0,0), (-1,-1), 1, colors.black),
                    ('FONTNAME', (0,0), (-1,-1),'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 7),
                    ]+weekend))
            items.append(tb)
            items.append(FrameBreak())
            
            t_data = [[t(self.language, "edit_stats_day"), t(self.language,"edit_stats_diffusers").replace("<br/>", "\n"), t(self.language,"edit_stats_pages"), t(self.language,"edit_stats_access")]]#+31*[4*[2]]
            weekend = []
            for k in d:
                if k>0: # first item holds max values
                    if self.stats.getWeekDay(k)>4:
                        weekend.append(('BACKGROUND',(0,k),(-1,k), colors.HexColor('#E6E6E6')))
                    t_data.append(['%02d.%s %s' %(k, t(self.language, "monthname_"+str(int(self.period[-2:]))+"_short"), self.period[:4]), len(d[k]["visitors"]), len(d[k]["different"]), len(d[k]["items"])])

            tb = Table(t_data, 4*[100], [25]+(len(d)-1)*[12])
            tb.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN',(0,0), (-1,-1), 'CENTER'),
                    ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
                    ('BOX', (0,0), (-1,-1), 1, colors.black),
                    ('FONTNAME', (0,0), (-1,-1),'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 7),
                    ('BACKGROUND',(1,0), (1,0), colors.HexColor('#fff11d')),
                    ('BACKGROUND',(2,0), (2,0), colors.HexColor('#2ea495')),
                    ('BACKGROUND',(3,0), (3,0), colors.HexColor('#84a5ef')),
                    ]+weekend))
            items.append(tb)
        return items
        
        
    def getStatDay(self, type):
        d = self.stats.getProgress('day')
        max = d[0]
        items = []
        
        h = 4*cm # max height
        l = 2*cm # left space
        b = 21.5*cm # bottom
        
        if type=="frames":
            items.append(Frame(1*cm, 26.0*cm, 19*cm, 1*cm,leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # header weekday
            for k in d:
                if k==0:
                    continue
                items.append(Frame(l+(k-1)*17, b, 16, len(d[k]["visitors"])*h/max["max_u"]+16, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # col 1
                items.append(Frame(l+(k-1)*17+5, b, 16, len(d[k]["different"])*h/max["max_p"]+16, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # col 2
                items.append(Frame(l+(k-1)*17+10, b, 16, len(d[k]["items"])*h/max["max"]+16, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # col 3
            
            items.append(Frame(l+5, b-1.1*cm, 119, 1.5*cm, id='normal', showBoundary=0))
            items.append(Frame(8*cm, b-1.4*cm, 11*cm, 6*cm, id='normal', showBoundary=0))

        if type=="data":
            items.append( Paragraph(t(self.language, "edit_stats_spreading_day"), self.chartheader))
            
            for k in d:
                if k==0:
                    continue
                items.append(PdfImage(config.basedir+"/web/img/stat_baruser_vert.png", width=5, height=len(d[k]["visitors"])*h/max["max_u"]+1))
                items.append(FrameBreak())
                items.append(PdfImage(config.basedir+"/web/img/stat_barpage_vert.png", width=5, height=len(d[k]["different"])*h/max["max_p"]+1))
                items.append(FrameBreak())
                items.append(PdfImage(config.basedir+"/web/img/stat_bar_vert.gif", width=6, height=len(d[k]["items"])*h/max["max"]+1))
                items.append(FrameBreak())

            tb = Table([[t(self.language, "dayname_"+str(x)+"_short") for x in range(0, 7)]], 7*[17], 17)
            tb.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('ALIGN',(0,0), (-1,-1), 'CENTER'),
                    ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
                    ('BOX', (0,0), (-1,-1), 1, colors.black),
                    ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 7),
                    ('BACKGROUND',(5,0),(-1,-1), colors.HexColor('#E6E6E6')),
                    ]))
            items.append(tb)
            items.append(FrameBreak())

            t_data = [[t(self.language, "dayname_"+str(x)+"_long")] for x in range(0, 7)]
            
            for k in d:
                if k==0:
                    continue
                t_data[k-1]+= [len(d[k][key]) for key in d[k].keys()]
            t_data = [[t(self.language, "edit_stats_weekday"),t(self.language,"edit_stats_diffusers").replace("<br/>", "\n"), t(self.language,"edit_stats_pages"), t(self.language,"edit_stats_access")]]+t_data
            
            tb = Table(t_data, 4*[70], [25]+7*[16])
            tb.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN',(0,0), (-1,-1), 'CENTER'),
                    ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
                    ('BOX', (0,0), (-1,-1), 1, colors.black),
                    ('FONTNAME', (0,0), (-1,-1),'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 7),
                    ('BACKGROUND',(1,0),(1,0), colors.HexColor('#fff11d')),
                    ('BACKGROUND',(2,0),(2,0), colors.HexColor('#2ea495')),
                    ('BACKGROUND',(3,0),(3,0), colors.HexColor('#84a5ef')),
                    ]))
            items.append(tb)
        return items

        
    def getStatTime(self, type):
        d = self.stats.getProgress('time')
        max = d[0]
        items = []
        h = 4*cm # max height
        
        if type=="frames":
            items.append(Frame(1*cm, 19.3*cm, 19*cm, 1*cm,leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # header time
            
            for k in d:
                if k==0:
                    continue
                items.append(Frame(1.67*cm+(k-1)*21, 14.8*cm, 6, (len(d[k]["visitors"])*h/max["max_u"])+16, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # row 1
                items.append(Frame(1.67*cm+(k-1)*21+6, 14.8*cm, 6, (len(d[k]["different"])*h/max["max_p"])+16, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # row 1
                items.append(Frame(1.67*cm+(k-1)*21+12, 14.8*cm, 6, (len(d[k]["items"])*h/max["max"])+16, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # row 1
            
            items.append(Frame(1*cm, 13.2*cm, 19*cm, 2*cm, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # legend
            items.append(Frame(1*cm, 1.0*cm, 19*cm, 12.5*cm, leftPadding=0, rightPadding=0, id='normal', showBoundary=0)) # value table
            
        if type=="data":
            items.append(Paragraph(t(self.language, "edit_stats_spreading_time"), self.chartheader))
            
            for k in d:
                if k==0:
                    continue
                items.append(PdfImage(config.basedir+"/web/img/stat_baruser_vert.png", width=6, height=len(d[k]["visitors"])*h/max["max_u"]+1))
                items.append(FrameBreak())
                items.append(PdfImage(config.basedir+"/web/img/stat_barpage_vert.png", width=6, height=len(d[k]["different"])*h/max["max_p"]+1))
                items.append(FrameBreak())
                items.append(PdfImage(config.basedir+"/web/img/stat_bar_vert.gif", width=6, height=len(d[k]["items"])*h/max["max"]+1))
                items.append(FrameBreak())

            t_data = []
            for i in range(0,24):
                im = PdfImage(config.basedir+"/web/img/stat_hr"+str(i%12+1)+".png", width=14, height=14)
                p = Paragraph((str(i)+"-"+str(i+1)), self.bv)
                t_data.append([p,im])
                
            tb = Table([t_data], 24*[21], [40])
            tb.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('ALIGN',(0,0),(-1,-1),'CENTER'),
                    ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
                    ('BOX', (0,0), (-1,-1), 1, colors.black),
                    ('FONTNAME', (0,0), (-1,-1),'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 7),
                    ]))
            items.append(tb)
            
            t_data = [['%02d:00-%02d:00' %(i, i+1)] for i in range(0,24)]
            for k in d:
                if k==0:
                    continue
                t_data[k-1] += [len(d[k][key]) for key in d[k].keys()]
            t_data = [[t(self.language, "edit_stats_daytime"),t(self.language,"edit_stats_diffusers").replace("<br/>", "\n"), t(self.language,"edit_stats_pages"), t(self.language,"edit_stats_access")]]+t_data

            tb = Table(t_data, 4*[70], [25]+[13]*24)
            tb.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                    ('ALIGN',(0,0),(-1,-1),'CENTER'),
                    ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
                    ('BOX', (0,0), (-1,-1), 1, colors.black),
                    ('FONTNAME', (0,0), (-1,-1),'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 7),
                    ('BACKGROUND',(1,0),(1,0), colors.HexColor('#fff11d')),
                    ('BACKGROUND',(2,0),(2,0), colors.HexColor('#2ea495')),
                    ('BACKGROUND',(3,0),(3,0), colors.HexColor('#84a5ef')),
                    ]))
            items.append(tb)
        return items
    
        
    def build(self, style=1):
        self.h1 = self.styleSheet['Heading1']
        self.h1.fontName = 'Helvetica'
        self.bv = self.styleSheet['BodyText']
        self.bv.fontName = 'Helvetica'
        self.bv.fontSize = 7
        self.bv.spaceBefore = 0
        self.bv.spaceAfter = 0
        
        self.chartheader = self.styleSheet['Heading3']
        self.chartheader.fontName = 'Helvetica'
        
        self.formatRight = self.styleSheet['Normal']
        self.bv.formatRight = 'Helvetica'
        self.formatRight.alignment = 2
        
        nameColl = self.collection.getName()

        while 1: 
            # page 1
            p = Paragraph("%s \n'%s'" %(t(self.language, "edit_stats_header"), nameColl), self.h1)
            p.wrap(defaultPageSize[0], defaultPageSize[1])

            if p.getActualLineWidths0()[0]<19*cm:
                break
            else:
                nameColl = nameColl[0:-4] + "..."

        self.data.append(p)

        self.data.append(Paragraph("%s: %s" %(t(self.language, "edit_stats_period_header"), self.period), self.chartheader))
        self.data.append(Paragraph(t(self.language, "edit_stats_pages_of")%("1", "4"), self.formatRight))
            
        self.data.append((FrameBreak()))
        # top 10
        self.data += self.getStatTop("data", namecut=60)
       
        # page 2
        self.data.append(Paragraph("%s \n'%s' %s - " %(t(self.language, "edit_stats_header"), self.collection.getName(), self.period) + t(self.language, "edit_stats_pages_of")%("2", "4"), self.bv))
        self.data.append((FrameBreak()))
        # country
        self.data += self.getStatCountry("data")
        self.data.append(PageBreak())
            
        # page 3
        self.data.append(Paragraph("%s \n'%s' %s - " %(t(self.language, "edit_stats_header"), self.collection.getName(), self.period) + t(self.language, "edit_stats_pages_of")%("3", "4"), self.bv))
        self.data.append((FrameBreak()))
        # date
        self.data += self.getStatDate("data")
        self.data.append(PageBreak())
            
        # page 4
        self.data.append(Paragraph("%s \n'%s' %s - " %(t(self.language, "edit_stats_header"), self.collection.getName(), self.period) + t(self.language, "edit_stats_pages_of")%("4", "4"), self.bv))
        self.data.append((FrameBreak()))
        # weekday
        self.data += self.getStatDay("data")  
        # time
        self.data += self.getStatTime("data")

        template = SimpleDocTemplate(config.get("paths.tempdir","") +"statsaccess.pdf",showBoundary=0)
        tFirst = PageTemplate(id='First', onPage=self.myPages, pagesize=defaultPageSize)
        tNext = PageTemplate(id='Later', onPage=self.myPages, pagesize=defaultPageSize)
            
        template.addPageTemplates([tFirst, tNext])
        template.allowSplitting = 1
        BaseDocTemplate.build(template, self.data)
                
        template.canv.setAuthor(t(self.language, "main_title"))
        template.canv.setTitle("%s \n'%s' - %s: %s" %(t(self.language, "edit_stats_header"), self.collection.getName(),t(self.language, "edit_stats_period_header"), self.period))
        return template.canv._doc.GetPDFData(template.canv)
    
def getPrintView(req):
    p = req.params.get("period")
    id = req.path.split("/")[2]
    node = tree.getNode(id)
    for f in node.getFiles():
        if f.getType()=="statistic":
            period, type = getPeriod(f.retrieveFile())
            if type==p.split("_")[0] and period==p.split("_")[1]:
                data = StatisticFile(f)
                
    if data:
        pdf = StatsAccessPDF(data, p.split("_")[1], id, lang(req))
        return pdf.build()
