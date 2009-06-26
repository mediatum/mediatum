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
import Image,ImageDraw
import core.config as config

try:
    from reportlab.platypus import Paragraph, BaseDocTemplate, SimpleDocTemplate, FrameBreak, Table, TableStyle, Image as PdfImage,Frame,PageBreak,PageTemplate
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.rl_config import defaultPageSize
    from reportlab.pdfgen import canvas
    reportlab=1
except:
    reportlab=0

from utils.utils import u, esc
from core.translation import t

class PrintPreview:
    def __init__(self, language, host=""):
        self.header = ""
        self.language = language
        self.host = host
        self.data = []
        self.image = 0
        self.styleSheet = getSampleStyleSheet()

        self.styleSheet.add(ParagraphStyle(name='paths',
                                  fontName='Helvetica-Bold',
                                  fontSize=10,
                                  spaceBefore=20,
                                  bulletFontName="Symbol",
                                  bulletFontSize=16))
                                  
        self.styleSheet.add(ParagraphStyle(name='fac_header',
                                  fontName='Helvetica-Bold',
                                  fontSize=10,
                                  leftIndent = 10,
                                  spaceBefore=10,
                                  spaceAfter=10))
        
        self.bl = self.styleSheet['Normal']
        self.bl.fontName = 'Helvetica-Bold'
        self.bl.spaceBefore=6

        self.bv = self.styleSheet['BodyText']
        self.bv.fontName = 'Helvetica'
        self.bv.spaceBefore = 0
        self.bv.spaceAfter = 5
        
        self.bf = self.styleSheet['fac_header']
        
        self.bp = self.styleSheet['paths']

        self.image_w = 9.5*cm
        self.image_h = 4.5*cm

    def myPages(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica',8)
        canvas.drawString(10*cm, 1.9*cm, "- %s %d -" % (t(self.language, "print_view_page"), doc.page))
        canvas.restoreState()


    def setHeader(self):
        h1 = self.styleSheet['Heading1']
        h1.fontName = 'Helvetica'
        self.header = Paragraph(t(self.language, "print_view_header"), h1)
        self.addData(self.header)
        self.addData(FrameBreak())

    def getStyle(self, page, config):
        frameHeader = Frame(1*cm, 25.5*cm, 19*cm, 3*cm,leftPadding=0, rightPadding=0, id='normal')
        frameFollow = Frame(1*cm, 2.5*cm, 19*cm, 26*cm,leftPadding=0, rightPadding=0, id='normal')

        if config==1:
            frameImage = Frame(1*cm, 2.5*cm, 9.5*cm, 23*cm,leftPadding=0, topPadding=12,rightPadding=0, id='normal')
            frameMeta = Frame(10.5*cm, 2.5*cm, 9.5*cm, 23*cm,leftPadding=10, rightPadding=0, id='normal')
            if page==1:
                return [frameHeader, frameImage, frameMeta]
            else:
                return [frameFollow]
        elif config==3:
            # liststyle for e.g. searchresults
            frameMeta = Frame(1*cm, 2.5*cm, 19*cm, 23*cm,leftPadding=10, rightPadding=0, id='normal')
            if page==1:
                return [frameHeader, frameMeta]
            else:
                return [frameFollow]
        else:
            frameImage = Frame(10.5*cm, 25.5*cm-self.image_h-1*cm, 9.5*cm, self.image_h+1*cm, leftPadding=0, rightPadding=0, id='normal')
            frameImage_hide = Frame(20.0*cm, 25.5*cm-self.image_h-1*cm, 0.01*cm, self.image_h+1*cm, leftPadding=0, rightPadding=0, id='normal')
            
            frameMeta = Frame(1*cm, 25.5*cm-self.image_h-1*cm, 9.5*cm, self.image_h+1*cm, leftPadding=10, topPadding=12, rightPadding=0, id='normal')
            frameMeta_hide = Frame(1*cm, 25.5*cm-self.image_h-1*cm, 19.0*cm, self.image_h+1*cm, leftPadding=10, topPadding=12, rightPadding=0, id='normal')
            frameMeta2 = Frame(1*cm, 2.5*cm, 19*cm, 23*cm-self.image_h-1*cm, leftPadding=10, rightPadding=0, id='normal')

            if page==1:
                if self.image==1:
                    return [frameHeader, frameImage, frameMeta, frameMeta2]
                else:
                    return [frameHeader, frameImage_hide, frameMeta_hide, frameMeta2]
            else:
                return [frameFollow]

    def build(self, style=1):
        template = SimpleDocTemplate(config.get("paths.tempdir","") +"print.pdf",showBoundary=0)
        tFirst = PageTemplate(id='First', frames=self.getStyle(1, style), onPage=self.myPages, pagesize=defaultPageSize)
        tNext = PageTemplate(id='Later', frames=self.getStyle(2, style), onPage=self.myPages, pagesize=defaultPageSize)
        
        template.addPageTemplates([tFirst, tNext])
        template.allowSplitting = 1
        BaseDocTemplate.build(template, self.data)
        return template.canv._doc.GetPDFData(template.canv)

    def addData(self, item):
        self.data.append(item)

    def addMetaData(self, metadata):
        """ format given metadatalist for pdf output """
        max_width = 0
        
        for item in metadata:
            l = Paragraph(item[2]+":", self.bl)
            
            if max_width<l.minWidth():
                max_width = l.minWidth()

        self.bv.leftIndent = max_width+10
        self.bv.bulletIndent = max_width+10

        for item in metadata:
            l = Paragraph(esc(item[2]+":"), self.bl)

            #if item[1].find("href")==-1:
            #    item[1] = esc(item[1])

            v = Paragraph(item[1], self.bv)

            self.addData(l)
            self.addData(v)


    def addImage(self, path):
        if not path:
            return
        if not os.path.isfile(path):
            path = config.basedir+"/web/img/questionmark.png"
        im = Image.open(path)
        im.load()
        self.image_w = 9.5*cm
        self.image_h = self.image_w/im.size[0]*im.size[1]
        self.data.append(PdfImage(path, width=self.image_w, height=self.image_h, kind="proportional"))
        self.image = 1
    
    def addPaths(self, pathlist):
        if len(pathlist)>0:
            self.addData(Paragraph(t(self.language, "print_preview_occurences")+":", self.bp))
            p = ' '
            for path in pathlist:

                for item in path:
                    p += '<link href="http://'+self.host+'/node?id='+item.id+'&amp;dir='+item.id+'\">'+item.getName()+ '</link>'

                    if path.index(item)<len(path)-1:
                        p += ' > '
                self.addData(Paragraph(p.replace('&', '&amp;'), self.bv, bulletText=u'\267'.encode("utf-8")))
                p = ' '
            
    def addChildren(self, children):
        self.addData(Paragraph(t(self.language, "print_view_children")+":", self.bp))

        # count headers
        _head = 0
        for c in children:
            if len(c)>0 and c[0][3]=="header":
                _head += 1

        items = []
        _c = 1
        for c in children:
            if len(c)>0 and c[0][3]=="header":
                if len(items)>0:
                    items.sort(lambda x, y: cmp(x[0].lower(),y[0].lower()))
                for item in items:
                    self.addData(Paragraph("["+str(_c)+"/"+str(len(children)-_head)+"]: "+"; ".join(item), self.bv))
                    _c+=1
                self.addData(Paragraph(u(c[0][1]).replace('&', '&amp;'), self.bf))
                items = []
               
                continue
            values = []
            for item in c:
                values.append(item[1])    
            items.append(values)

        # print last items   
        if len(items)>0:
            items.sort(lambda x, y: cmp(x[0].lower(),y[0].lower()))
        for item in items:
            self.addData(Paragraph("["+str(_c)+"/"+str(len(children)-_head)+"]: "+", ".join(item), self.bv))
            _c+=1    

            
def getPrintView(lang, imagepath, metadata, paths, style=1, children=[]): # style=1: object, style=3: liststyle
    """ returns pdf content of given item """
    if not reportlab:
        return None

    pv = PrintPreview(lang, config.get("host.name"))
    pv.setHeader()
    
    if style==1 or style==2:
        # single object (with children)
        pv.addImage(imagepath)
        pv.addData(FrameBreak())
        pv.addMetaData(metadata)

        pv.addPaths(paths)
        if len(children)>0:
            pv.addData(FrameBreak())
        
        pv.addChildren(children)
    elif style==3:
        # objectlist
        pv.addData(Paragraph(t(pv.language, "print_view_list"), pv.bp))
        pv.addChildren(children)
            
    return pv.build(style)
