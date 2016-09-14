# -*- coding: utf-8 -*-
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
import re
from mediatumtal import tal
from utils.utils import esc
from core.metatype import Metatype
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import sys
import traceback
from utils.utils import splitfilename
import core.config as config


logg = logging.getLogger(__name__)

FONTPATH = "/utils/ArenaBlack.ttf"
FONTSIZE = 40


class m_watermark(Metatype):

    """ This class implements the metatype watermark and everything that is needed to handle it """

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL("metadata/watermark.html", {"lock": lock,
                                                      "value": value,
                                                      "width": width,
                                                      "name": field.getName(),
                                                      "field": field,
                                                      "required": self.is_required(required)},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/watermark.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        if html:
            value = esc(value)
        # replace variables
        for var in re.findall(r'&lt;(.+?)&gt;', value):
            if var == "att:id":
                value = value.replace("&lt;" + var + "&gt;", unicode(node.id))
            elif var.startswith("att:"):
                val = node.get(var[4:])
                if val == "":
                    val = "____"

                value = value.replace("&lt;" + var + "&gt;", val)

        return (metafield.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item)
        try:
            return value.replace("; ", ";")
        except:
            logg.exception("exception in format_request_value_for_db, returning value")
            return value

    def getName(self):
        return "fieldtype_watermark"

    ''' generate watermark '''

    def reduce_opacity(self, im, opacity):
        """Reduces the opacity of an image. Opacity must be between 0 and 1"""
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
        else:
            im = im.copy()
        alpha = im.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        im.putalpha(alpha)
        return im

    def watermark(self, image, imagewm, text, opacity):
        """ Creates a watermark, defined by an arbitrary string and draws it on an image"""
        im = None
        draw = None
        mark = None
        layer = None
        drawwater = None
        try:
            try:
                im = Image.open(image)
                im = im.copy()
                if im.mode != 'RGBA':
                    logg.info("Converting image to RGBA!")
                    im = im.convert('RGBA')
                draw = ImageDraw.Draw(im)

                # Load a custom font
                font = None
                try:
                    font = ImageFont.truetype(config.basedir + FONTPATH, FONTSIZE)
                except Exception:
                    logg.exception("Loading of custom font failed, using default")
                    font = ImageFont.load_default()

                # Now measure size of text if it would be created with the new font and create a custom bitmap
                text_size = draw.textsize(text, font=font)
                mark = Image.new("RGBA", text_size, (0, 0, 0, 0))
                layer = Image.new("RGBA", im.size, (0, 0, 0, 0))

                # Create drawing object and draw text on bitmap
                drawwater = ImageDraw.Draw(mark)
                drawwater.text((0, 0), text, font=font, fill=(0, 0, 0, 255))

                pos_x = 0
                pos_y = 0
                width = mark.size[0]
                height = mark.size[1]

                if mark.size[0] > im.size[0]:
                    width = im.size[0]

                if mark.size[1] > im.size[1]:
                    height = im.size[1]

                mark = mark.resize((width, height))

                pos_x = im.size[0] / 2 - width / 2
                pos_y = im.size[1] / 2 - height / 2
                # Paste mark on layer
                layer.paste(mark, (pos_x, pos_y))
                layer = self.reduce_opacity(layer, opacity)

                im = Image.composite(layer, im, layer)
                im.save(imagewm, "JPEG")
                logg.info("Finished creating watermark")

            except:
                logg.exception("Exception while creating the watermark")
                im = image
        finally:
            del draw
            del drawwater
            del mark
            del layer
        return im

    ''' events '''

    def event_metafield_changed(self, node, field):
        if "image" in node.type:
            items = node.attrs.items()
            # check if there is an original file and modify it in case
            for f in node.getFiles():
                if f.type == "original":
                    path, ext = splitfilename(f.retrieveFile())
                    pngname = path + "_wm.jpg"

                    for file in node.getFiles():
                        if file.getType() == "original_wm":
                            node.removeFile(file)
                            break
                    self.watermark(f.retrieveFile(), pngname, node.get(field.getName()), 0.6)
                    node.addFile(FileNode(name=pngname, type="original_wm", mimetype="image/jpeg"))
                    logg.info("watermark created for original file")

    # method for additional keys of type watermark
    def getLabels(self):
        return m_watermark.labels

    labels = {"de":
              [
                  ("fieldtype_watermark", "Wasserzeichen"),
                  ("fieldtye_watermark_desc", u"Wasserzeichen für Bilder")
              ],
              "en":
              [
                  ("fieldtype_watermark", "watermark"),
                  ("fieldtype_watermark_desc", "watermark for images")
              ]
              }
