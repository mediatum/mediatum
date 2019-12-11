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

import logging
import random
from PIL import Image, ImageDraw
from core import config
import os
from subprocess import CalledProcessError
from utils.utils import suppress as _suppress
import utils.process
import codecs

logging.basicConfig()

logg = logging.getLogger(__name__)


class PDFException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class PDFInfo(object):

    def __init__(self, data={}):
        self.data = data

    def getInfo(self, name):
        if name in self.data.keys():
            return self.data[name]
        return ""

    def isEncrypted(self):
        if self.getInfo("Encrypted") == "yes":
            return 1
        return 0

    def __getitem__(self, key):
        return self.data[key]

    def items(self):
        return self.data


def parsePDF(filename, tempdir):
    # process info file
    def parseInfo(lines):
        attrs = ["Title", "Subject", "Keywords", "Author", "Creator", "Producer", "CreationDate", "ModDate",
                 "Tagged", "Pages", "Encrypted", "Page size", "File size", "Optimized", "PDF Version", "Metadata"]
        data = {}
        for line in lines:
            for attr in attrs:
                parts = line.replace("\n", "").replace("\r", "").split(attr + ":")
                if len(parts) == 2:
                    # pdfinfo cannot handle strings in utf-16, they are clipped after BOM_UTF16_BE:
                    if parts[1].strip() == codecs.BOM_UTF16_BE:
                        break
                    data[attr] = parts[1].strip()

                    if attr == "Encrypted" and parts[1].strip().startswith("yes"):
                        for s_option in parts[1].strip()[5:-1].split(" "):
                            option = s_option.split(":")
                            if option[1] == "":
                                break
                            data[option[0]] = option[1]
                        data[attr] = "yes"
                    break
        return PDFInfo(data)

    name = ".".join(filename.split(".")[:-1])
    imgfile = os.path.join(tempdir, "tmp" + str(random.random()) + ".png")
    thumb128 = name + ".thumb"
    thumb300 = name + ".thumb2"
    fulltext_from_pdftotext = name + ".pdftotext"  # output of pdf to text, possibly not normalized utf-8
    fulltext = name + ".txt"  # normalized output of uconv
    infoname = name + ".info"

    info_cmd = ["pdfinfo", filename]
    try:
        out = utils.process.check_output(info_cmd)
    except CalledProcessError:
        logg.exception("failed to extract metadata from file %s")
        info = PDFInfo()
    else:
        info = parseInfo(out.splitlines())

    # test for correct rights
    if info.isEncrypted():
        raise PDFException("error:document encrypted")

    finfo = open(infoname, "w")
    for item in info.items():  # infokeys:
        finfo.write(item + ":" + (" " * (15 - len(item)) + info[item] + "\n"))
    finfo.close()

    # convert first page to image (graphicsmagick + ghostview)
    # use convert command from config if defined
    convert_cmd = config.get("external.convert_cmd", "")
    if convert_cmd and convert_cmd.find("pdf_file") >= 0 and convert_cmd.find("image_file") >= 0:
       convert_cmd = convert_cmd.replace("pdf_file", filename + "[0]")
       convert_cmd = convert_cmd.replace("image_file", imgfile)
       convert_cmd = convert_cmd.split(' ')
    else:
        convert_cmd = ["gm", "convert", "-colorspace", "RGB", "-density", "300",
                       filename + "[0]", "-background", "white", "-thumbnail", "x300", imgfile]
    try:
        utils.process.check_call(convert_cmd)
    except CalledProcessError:
        logg.exception("failed to create PDF thumbnail for file " + filename)
    else:
        makeThumbs(imgfile, thumb128, thumb300)

    # extract fulltext (xpdf)
    fulltext_cmd = ["pdftotext", "-enc", "UTF-8", filename, fulltext_from_pdftotext]
    try:
        utils.process.check_call(fulltext_cmd)
    except CalledProcessError:
        logg.exception("failed to extract fulltext from file %s", filename)

    # normalization of fulltext (uconv)
    fulltext_normalization_cmd = ["uconv", "-x", "any-nfc", "-f", "UTF-8", "-t", "UTF-8", "--output", fulltext, fulltext_from_pdftotext]
    try:
        utils.process.check_call(fulltext_normalization_cmd)
    except CalledProcessError:
        logg.exception("failed to normalize fulltext from file %s", filename)

    with _suppress(OSError, warn=False):
        os.remove(fulltext_from_pdftotext)
    with _suppress(OSError, warn=False):
        os.remove(imgfile)


def makeThumbs(src, thumb128, thumb300):
    """create preview image for given pdf """
    pic = Image.open(src)
    pic.load()
    pic = pic.convert("RGB")
    width = pic.size[0]
    height = pic.size[1]

    if width > height:
        newwidth, newheight = 300, height * 300 / width
    else:
        newwidth, newheight = width * 300 / height, 300

    pic = pic.resize((newwidth, newheight), Image.ANTIALIAS)
    im = Image.new("RGB", (300, 300), (255, 255, 255))
    x = (300 - newwidth) / 2
    y = (300 - newheight) / 2
    im.paste(pic, (x, y, x + newwidth, y + newheight))
    draw = ImageDraw.ImageDraw(im)
    draw.line([(x, y), (x + newwidth, y), (x + newwidth, y + newheight), (x, y + newheight), (x, y)], (200, 200, 200))

    draw.line([(0, 0), (299, 0), (299, 299), (0, 299), (0, 0)], (128, 128, 128))
    im.save(thumb300, "jpeg")

    im = im.resize((128, 128), Image.ANTIALIAS)
    draw = ImageDraw.ImageDraw(im)
    draw.line([(0, 0), (127, 0), (127, 127), (0, 127), (0, 0)], (128, 128, 128))
    im.save(thumb128, "jpeg")
