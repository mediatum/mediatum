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
import sys
if __name__ == "__main__":
    sys.path += [sys.argv[1]]

import gfx
import logging
from utils.dicts import SortedDict
import random
import Image
import ImageDraw
import logging
import sys
import os

from utils.utils import splitfilename

class EncryptedException:
    pass

def parsePDF(filename):
    import core.config as config
    tempdir = config.get("paths.tempdir")
    name, ext = splitfilename(filename)
    
    thumb128 = name+".thumb"
    thumb300 = name+".thumb2"
    fulltext = name+".txt"
    infoname = name+".info"

    gfx.verbose(0)
    gfx.setoption("disable_polygon_conversion", "1")
    pdf = gfx.open("pdf", filename)
    
    if pdf.getInfo("oktocopy") != "yes":
        raise EncryptedException()

    png = gfx.ImageList()
    txt = gfx.PlainText()

    maxwidth,maxheight = 0,0
    for pagenr in range(1,pdf.pages+1):
        page = pdf.getPage(pagenr)
        txt.startpage(page.width, page.height)
        page.render(txt)
        txt.endpage()
        if page.width > maxwidth:
            maxwidth = page.width
        if page.height > maxheight:
            maxheight = page.height
        if pagenr == 1:
            png.startpage(page.width, page.height)
            page.render(png)
            png.endpage()

    infodict = SortedDict()
    infodict["producer"] = pdf.getInfo("producer")
    infodict["creationdate"] = pdf.getInfo("creationdate")
    infodict["tagged"] = pdf.getInfo("tagged")
    infodict["pages"] = str(pdf.pages)
    infodict["pagesize"] = "%d x %d pts" % (maxwidth, maxheight)
    infodict["title"] = pdf.getInfo("title")
    infodict["subject"] = pdf.getInfo("subject")
    infodict["keywords"] = pdf.getInfo("keywords")
    infodict["author"] = pdf.getInfo("author")
    infodict["creator"] = pdf.getInfo("creator")
    infodict["moddate"] = pdf.getInfo("moddate")
    infodict["linearized"] = pdf.getInfo("linearized")
    infodict["encrypted"] = pdf.getInfo("encrypted")
    infodict["print"] = pdf.getInfo("oktoprint")
    infodict["copy"] = pdf.getInfo("oktocopy")
    infodict["change"] = pdf.getInfo("oktochange")
    infodict["addNotes"] = pdf.getInfo("oktoaddnotes")
    infodict["version"] = pdf.getInfo("version")
                
    fi = open(infoname, "wb")
    for k,v in infodict.items():
        if v:
            fi.write(k+":"+(" "*(16-len(k))+v+"\n"))
    fi.close()

    imgfile = tempdir + "tmp" + str(random.random())
    png.save(imgfile)
    makeThumbs(imgfile, thumb128, thumb300)
    try: os.unlink(imgfile)
    except: pass

    # if xpdf exists, use it- it might generate better fulltext than gfx
    try:
        os.system("pdftotext -enc UTF-8 " + filename + " " + fulltext)
    except:
        txt.save(fulltext)

def parsePDF2(filename):
    from core.config import basedir
    command = "\"\"%s\" \"%s\" \"%s\"" % (sys.executable, os.path.join(basedir,"lib/pdf/parsepdf.py"), filename)
    os.system(command)
    
    exit_status = os.system(command) >> 8
    
    if exit_status:
        logging.getLogger('errors').error("Exit status "+str(exit_status)+" of subprocess "+command)
    if exit_status == 111:
        raise EncryptedException()

"""  create preview image for given pdf """
def makeThumbs(src, thumb128, thumb300):
    pic = Image.open(src)
    pic.load()
    pic = pic.convert("RGB")
    width = pic.size[0]
    height = pic.size[1]

    if width > height: newwidth,newheight = 300,height*300/width
    else:              newwidth,newheight = width*300/height,300

    pic = pic.resize((newwidth, newheight), Image.ANTIALIAS)
    im = Image.new("RGB", (300, 300), (255, 255, 255))
    x = (300-newwidth)/2
    y = (300-newheight)/2
    im.paste( pic, (x,y,x+newwidth,y+newheight))
    draw = ImageDraw.ImageDraw(im)
    draw.line([(x,y),(x+newwidth,y),(x+newwidth,y+newheight),(x,y+newheight),(x,y)], (200,200,200))

    draw.line([(0,0),(299,0),(299,299),(0,299),(0,0)], (128,128,128))
    im.save(thumb300,"jpeg")

    im = im.resize((128, 128),Image.ANTIALIAS)
    draw = ImageDraw.ImageDraw(im)
    draw.line([(0,0),(127,0),(127,127),(0,127),(0,0)], (128,128,128))
    im.save(thumb128,"jpeg")

if __name__ == "__main__":
    import sys

    try:
        import signal
        signal.alarm(600) # try processing the file for 10 minutes - then abort
    except:
        pass
    try:
        parsePDF(sys.argv[1])

    except EncryptedException:
        sys.exit(111)

