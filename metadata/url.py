# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal
import logging
import re

import core.translation as _core_translation
from core.metatype import Metatype
from urllib import unquote
from utils.utils import quote_uri
from utils.strings import ensure_unicode_returned
from utils.strings import replace_attribute_variables


logg = logging.getLogger(__name__)


@ensure_unicode_returned
def _replace_vars(node, s):
    s = replace_attribute_variables(s, node.id, node.get_special, r'<(.+?)>', "<", ">")
    s = replace_attribute_variables(s, node.id, node.get_special, r'\[(.+?)\]', "[", "]")
    return s


_icons = {"externer Link": "/static/img/extlink.png", "Email": "/static/img/email.png"}
_targets = {"selbes Fenster": "same", "neues Fenster": "_blank"}


class m_url(Metatype):

    name = "url"

    default_settings = dict(
        link="",
        text="",
        icon="",
        new_window=False,
    )

    def editor_get_html_form(self, field, value="", width=400, lock=0, language=None, required=None):
        metacfg = field.metatype_data
        link, text = (value.split(";")+[""])[:2]
        return tal.getTAL(
                "metadata/url.html",
                dict(
                    lock=lock,
                    link=link or metacfg["link"],
                    text=text or metacfg["text"],
                    width=width,
                    name=field.getName(),
                    field=field,
                    required=1 if required else None,
                   ),
                macro="editorfield",
                language=language,
               )

    def search_get_html_form(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/url.html",
                dict(
                    name=name,
                    value=value,
                   ),
                macro="searchfield",
                language=language,
               )

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html=True):
        value = (node.get(metafield.getName()).split(";") + ["", "", "", ""])[0:4]
        metacfg = metafield.metatype_data
        link, text, icon = (
                _replace_vars(node, unicode(v or f))
                for v, f in zip(value[:3], (metacfg["link"], metacfg["text"], metacfg["icon"]))
               )

        # find unsatisfied variables
        if "____" in link:
            link = u''
        if "____" in text:
            text = u''
        if link and not text:
            text = unquote(link)
        if not (link or text):
            value = icon = u""
        elif text and not link:
            value = text
            icon = u""
        elif value[3] != "same" or metacfg["new_window"]:
            value = u'<a href="{}" target="_blank" title="{}">{}</a>'.format(
                    link,
                    _core_translation.translate_in_request('show_in_new_window'),
                    text,
                )
        else:
            value = u'<a href="{}">{}</a>'.format(link, text)
        if icon:
            value += u'<img src="{}"/>'.format(icon)

        return metafield.getLabel(), value

    def editor_parse_form_data(self, field, form):
        uri = form.get(field.name)
        quoted_uri = quote_uri(uri)
        if not quoted_uri:
            return ""
        linktext = form.get("{}_text".format(field.name)).replace(u";", u"\u037e")
        if not linktext:
            # don't add a single ';' add the end of the url (quoted_uri)
            return u"{}".format(quoted_uri)
        return u"{};{}".format(quoted_uri, linktext)

    def admin_settings_get_html_form(self, fielddata, metadatatype, language):
        return tal.getTAL(
            "metadata/url.html",
            dict(
                link=fielddata["link"],
                text=fielddata["text"],
                icon=fielddata["icon"],
                new_window=fielddata["new_window"],
                icons=_icons,
                url_targets=_targets,
            ),
            macro="metafieldeditor",
            language=language,
        )

    def admin_settings_parse_form_data(self, data):
        assert data.get("new_window") in (None, "1")
        return dict(
            link=data["link"],
            text=data["text"],
            icon=data["icon"],
            new_window=bool(data.get("new_window")),
        )

    translation_labels = dict(
        de=dict(
            url_edit_link="Link:",
            url_edit_linktext="Angezeigter Text:",
            url_edit_icon="Icon:",
            url_edit_noicon="-kein Icon-",
            url_edit_preview="Vorschau:",
            url_urltarget="Neues Fenster:",
            fieldtype_url="URL",
            fieldtype_url_desc="externer Link (neues Fenster)",
        ),
        en=dict(
            url_edit_link="Link:",
            url_edit_linktext="Link Text:",
            url_edit_icon="Icon:",
            url_edit_noicon="-kein Icon-",
            url_edit_preview="Preview:",
            url_urltarget="New window:",
            fieldtype_url="url",
            fieldtype_url_desc="external link (new window)",
        ),
    )
