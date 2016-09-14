"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Werner Neudenberger <neudenberger@ub.tum.de>


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
import random
import string
import StringIO

from PIL import Image, ImageDraw

from datetime import datetime

from reportlab.pdfgen import canvas
from pyPdf import PdfFileWriter, PdfFileReader

import core.config as config
import utils.process


def get_pdf_page_image(pdfpath, page, prefix="_PdfPageImage_%(testname)s_%(page)s_.png", path_only=False):

    tmppath = config.get("paths.datadir") + "tmp/"
    testname = "_testname_"
    tmpname = prefix % {'testname': testname, 'page': page}

    tmppng = tmppath + tmpname

    if not path_only:
        utils.process.call(("convert", "-alpha", "off", "-colorspace", "RGB",
                            "{}[{}]".format(pdfpath, page), tmppng))
    return tmppng


def get_pdf_dimensions(fn):

    d = {}
    f = open(fn, "rb")
    pdf = PdfFileReader(f)
    numPages = pdf.getNumPages()
    d['numPages'] = numPages
    d_pages = {}
    d_pageno2size = {}
    d_pageno2rotate = {}
    for i in xrange(numPages):
        p = pdf.getPage(i)
        x0 = x1 = y0 = y1 = 0.0
        for k in ['/TrimBox', '/CropBox', '/MediaBox', '/ArtBox']:
            try:
                _dim = p[k]
            except:
                continue
            _x0, _y0, _x1, _y1 = map(float, _dim)
            y0 = min(y0, _y0)
            y1 = max(y1, _y1)
            x0 = min(x0, _x0)
            x1 = max(x1, _x1)
        width = x1 - x0
        height = y1 - y0
        key = unicode([width, height])
        d_pages[key] = d_pages.get(key, []) + [i]
        d_pageno2size[i] = [width, height]

        rotate = p.get('/Rotate', 0)
        try:
            d_pageno2rotate[i] = int(rotate.real)
        except:
            d_pageno2rotate[i] = int(rotate)

    d['d_pages'] = d_pages
    d['d_pageno2size'] = d_pageno2size
    d['d_pageno2rotate'] = d_pageno2rotate

    f.close()

    return d


def get_pdf_pagecount(fn):
    f = open(fn, "rb")
    pdf = PdfFileReader(f)
    numPages = pdf.getNumPages()
    f.close()
    return numPages


def get_pdf_pagesize(fn, page=0):
    f = open(fn, "rb")
    pdf = PdfFileReader(f)
    p = pdf.getPage(page)
    f.close()
    x0 = x1 = y0 = y1 = 0.0
    for k in ['/TrimBox', '/CropBox', '/MediaBox', '/ArtBox', ]:
        try:
            _dim = p[k]
        except:
            continue
        _x0, _y0, _x1, _y1 = map(float, _dim)
        y0 = min(y0, _y0)
        y1 = max(y1, _y1)
        x0 = min(x0, _x0)
        x1 = max(x1, _x1)
    width = x1 - x0
    height = y1 - y0
    return (width, height)


def get_pic_size(fn):
    pic = Image.open(fn)
    pic.load()
    return pic.size


def get_pic_info(fn):
    pic = Image.open(fn)
    pic.load()
    return pic.info


def get_pic_dpi(fn):
    pic = Image.open(fn)
    pic.load()
    dpi = pic.info.get('dpi', ('no-info', 'no-info'))[0]
    return dpi


def place_pic(fn_in, fn_pic, fn_out, x0, y0, scale=1.0, mask=None, pages=[], follow_rotate=False):

    pdf = PdfFileReader(file(fn_in, "rb"))

    output = PdfFileWriter()
    outputStream = file(fn_out, "wb")

    width, height = pic_pdf_size = get_pdf_pagesize(fn_in)
    pdf_dim = get_pdf_dimensions(fn_in)
    pic_width, pic_height = get_pic_size(fn_pic)

    pagecount = pdf_dim['numPages']

    d_watermark = {}

    for i in range(pagecount):

        p = pdf.getPage(i)

        if i in pages:
            rotate = int(pdf_dim['d_pageno2rotate'][i]) % 360
            w, h = pdf_dim['d_pageno2size'][i]
            max_wh = max(w, h)
            translation_scale = 1.0
            key = "%.3f|%.3f|%d" % (float(w), float(h), int(rotate))
            if key in d_watermark:
                watermark = d_watermark[key][0]
            else:
                s_out = StringIO.StringIO()
                c = canvas.Canvas(s_out, pagesize=(w, h))
                x1 = x0 * translation_scale
                y1 = y0 * translation_scale - 0.51
                if rotate and not follow_rotate:

                    if rotate == 90:
                        c.translate(w, 0)
                    elif rotate == 180:
                        c.translate(w, h)
                    elif rotate == 270:
                        c.translate(0, h)

                    c.rotate(rotate)

                c.drawImage(fn_pic,
                            x1,
                            y1,
                            width=int(pic_width * scale + 0.5),
                            height=int(pic_height * scale + 0.5),
                            preserveAspectRatio=True,
                            mask=mask)
                c.save()

                watermark = PdfFileReader(s_out)
                d_watermark[key] = (watermark, s_out)

            p.mergePage(watermark.getPage(0))

        output.addPage(p)

    output.write(outputStream)

    outputStream.close()

    for k in d_watermark:
        try:
            d_watermark[k][1].close()
        except:
            pass

    pdf.stream.close()

    return


def build_logo_overlay_pdf(fn_matrix_pdf,
                           fn_pic, fn_out,
                           x0,
                           y0,
                           scale=1.0,
                           mask=None,
                           pages='auto',  # [],
                           follow_rotate=False,
                           url=''):

    str_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    #str_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    fn_logo_temp = fn_matrix_pdf.replace(".pdf", "__logo_temp__" + str_datetime + ".pdf")

    pdf_dim = get_pdf_dimensions(fn_matrix_pdf)
    pagecount = pdf_dim['numPages']
    pic_width, pic_height = get_pic_size(fn_pic)

    output = PdfFileWriter()
    outputStream = file(fn_logo_temp, "wb")

    for i in range(pagecount):

        rotate = int(pdf_dim['d_pageno2rotate'][i]) % 360
        w, h = pdf_dim['d_pageno2size'][i]
        translation_scale = 1.0

        s_out = StringIO.StringIO()

        if rotate % 180:
            c = canvas.Canvas(s_out, pagesize=(h, w))
        else:
            c = canvas.Canvas(s_out, pagesize=(w, h))

        x1 = x0 * translation_scale
        y1 = y0 * translation_scale - 0.51

        if rotate and not follow_rotate:

            if rotate == 90:
                c.translate(w, 0)
            elif rotate == 180:
                c.translate(w, h)
            elif rotate == 270:
                c.translate(0, h)

            c.rotate(rotate)

        c.setFont("Helvetica", 10.5)

        if i in pages:

            width = int(pic_width * scale + 0.5)
            height = int(pic_height * scale + 0.5)

            c.drawImage(fn_pic,
                        x1,
                        y1,
                        width=int(pic_width * scale + 0.5),
                        height=int(pic_height * scale + 0.5),
                        preserveAspectRatio=True,
                        mask=mask)

            if url:
                pass

                #r1 = (x1, y1, x1 + width, y1 + height)
                #
                # c.linkURL(url,
                #          r1,
                #          thickness=1,
                #          color=colors.green)

                c.drawString(x1 + int(pic_width * scale + 0.5), y1 + int(pic_height * scale + 0.5) / 2, url)

        else:
            c.drawString(0, 0, '')

        c.save()

        watermark = PdfFileReader(s_out)

        p = watermark.getPage(0)

        output.addPage(p)

    output.write(outputStream)

    outputStream.close()
    utils.process.call(("pdftk", fn_matrix_pdf, "multistamp", fn_logo_temp, "output", fn_out))
    return


def parse_printer_range(s, minimum=1, maximum=100, sep=";", firstpage_has_pageno=1):
    res = set()
    for part in [part.strip() for part in s.split(sep) if part.strip()]:
        x = [x.strip() for x in part.split('-')]
        if part.count('-') == 0:
            val = int(x[0])
            if minimum <= val < maximum:
                res.update([val])
            else:
                pass
        elif part.count('-') == 1:
            if len(x) == 2:
                a, b = x
                if a and b:
                    res.update(range(max(int(a), minimum), min(int(b) + 1, maximum)))
                elif a:
                    res.update(range(max(int(a), minimum), maximum))
                else:
                    raise ValueError("syntax error")
            else:
                # should not happen
                raise ValueError("unexpected error")
        else:
            raise ValueError("multiple '-'")
    res = sorted(list(res))
    res = [x - firstpage_has_pageno for x in res]
    return res


def getGridBuffer(pdf_size, thumb_size, dpi, thick=5, orig=["top_left", "bottom_left"][1], orig_message='origin', rotate=0):

    if not (rotate % 180):
        (pdf_w, pdf_h) = pdf_size
    else:
        (pdf_h, pdf_w) = pdf_size

    (thumb_w, thumb_h) = thumb_size
    (dpi_w, dpi_h) = dpi

    count_cm_h = 2.54 * pdf_h / dpi_h
    count_cm_w = 2.54 * pdf_w / dpi_w

    w, h = int(thumb_w + 1), int(thumb_h + 1)
    img = Image.new("RGB", (w, h), "#FFFFFF")

    draw = ImageDraw.Draw(img)

    fx = 1.0 * thumb_w / count_cm_w
    for i in range(0, int(count_cm_w + 1)):
        x = i * fx
        draw.line((x, 0) + (x, h), fill="red")
        if thick and (i % thick == 0):
            draw.line((x - 1, 0) + (x - 1, h), fill="red")
            #draw.line((x + 1, 0) + (x + 1, h), fill="red")

    fy = 1.0 * thumb_h / count_cm_h
    if orig == "top_left":
        draw.ellipse([-0.5 * fx, -0.5 * fy, 0.5 * fx, 0.5 * fy], outline="red")
        draw.text((0.5 * fx, 0.25 * fy), orig_message, fill="blue")
        for i in range(0, int(count_cm_h + 1)):
            y = i * fy
            draw.line((0, y) + (w, y), fill="red")
            if thick and (i % thick == 0) and i > 0:
                #draw.line((0, y - 1) + (w, y - 1), fill="red")
                draw.line((0, y + 1) + (w, y + 1), fill="red")
    else:
        draw.ellipse([-0.5 * fx, thumb_h - 0.5 * fy, 0.5 * fx, thumb_h + 0.5 * fy], outline="red")
        draw.text((0.5 * fx, thumb_h - 0.75 * fy), orig_message, fill="blue")
        for i in range(0, int(count_cm_h + 1)):
            y = i * fy
            draw.line((0, thumb_h - y) + (w, thumb_h - y), fill="red")
            if thick and (i % thick == 0) and i > 0:
                draw.line((0, thumb_h - y - 1) + (w, thumb_h - y - 1), fill="red")
                #draw.line((0, thumb_h - y + 1) + (w, thumb_h - y + 1), fill="red")

    img = img.convert("RGBA")

    data = img.getdata()
    new_data = list()

    for item in data:
        if item[0:3] == (255, 255, 255):
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    img.putdata(new_data)

    f = StringIO.StringIO()
    img.save(f, "PNG")

    return f
