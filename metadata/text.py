# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import re
from mediatumtal import tal
from core import httpstatus
import core.config as config
from utils.utils import esc
from utils.utils import modify_tex
from core.metatype import Metatype, charmap
from utils.strings import replace_attribute_variables
from web import frontend as _web_frontend

logg = logging.getLogger(__name__)


class m_text(Metatype):

    name = "text"

    def editor_get_html_form(self, field, value="", width=40, lock=0, language=None, required=None):
        try:
            field_node_name = field.name
        except:
            field_node_name = None

        return tal.getTAL(
                "metadata/text.html",
                dict(
                    lock=lock,
                    value=value,
                    width=width,
                    name=field_node_name,
                    field=field,
                    ident=field.id if field.id else "",
                    required=1 if required else None,
                   ),
                macro="editorfield",
                language=language,
               )

    def search_get_html_form(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/text.html",
                dict(
                    name=name,
                    value=value,
                   ),
                macro="searchfield",
                language=language,
               )

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html=True, template_from_caller=None):

        value = node.get_special(metafield.name)
        # consider int, long values like filesize
        if isinstance(value, (int, long)):
            value = str(value)
        value = value.replace(";", "; ")

        # ignore trailing newlines for textfields
        value = value.rstrip("\r\n")

        if html:
            value = esc(value)

        # replace variables
        # substitute TeX sub/super-scripts with <sub>/<sup> html tags
        value = modify_tex(value, 'html')

        value = replace_attribute_variables(value, node.id, node.get, r'&lt;(.+?)&gt;', "&lt;", "&gt;")
        value = value.replace("&lt;", "<").replace("&gt;", ">")

        if not maskitem:
            return (metafield.getLabel(), value)

        # use default value from mask if value is empty
        if value == u'':
            value = maskitem.getDefault()

        return (metafield.getLabel(), value)

    # method for popup methods of type text
    def getPopup(self, req):
        req.response.set_data(tal.processTAL(
                dict(
                    charmap=charmap,
                    name=req.values.get("name"),
                    value=req.values.get("value"),
                    html_head_style_src=_web_frontend.html_head_style_src,
                    html_head_javascript_src=_web_frontend.html_head_javascript_src,
                ),
                file="metadata/text.html",
                macro="popup",
                request=req,
            ))
        req.response.status_code = httpstatus.HTTP_OK
        return httpstatus.HTTP_OK
