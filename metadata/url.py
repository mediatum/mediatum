# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal
import logging
import re
from core.metatype import Metatype
from core.translation import t
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


_icons = {"externer Link": "/img/extlink.png", "Email": "/img/email.png"}
_targets = {"selbes Fenster": "same", "neues Fenster": "_blank"}


class m_url(Metatype):

    name = "url"

    default_settings = dict(
        link="",
        text="",
        icon="",
        new_window=False,
    )

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
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

    def getSearchHTML(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/url.html",
                dict(
                    name=name,
                    value=value,
                   ),
                macro="searchfield",
                language=language,
               )

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        try:
            value = (node.get(metafield.getName()).split(";") + ["", "", "", ""])[0:4]
            metacfg = metafield.metatype_data
            fielddef = (
                    metacfg["link"],
                    metacfg["text"],
                    metacfg["icon"],
            )

            l = []
            for i in range(0, 3):
                try:
                    if value[i]:
                        l.append(value[i])
                    else:
                        l.append(fielddef[i])
                except:
                    l.append(fielddef[i])

            link, text, icon = [_replace_vars(node, str(p)) for p in l]
            new_window = value[3] != "same" or metacfg["new_window"]

            # find unsatisfied variables
            if link.find("____") >= 0:
                link = u''
            if text.find("____") >= 0:
                text = u''

            if len(fielddef) < 4:
                target = u""
            if link != "" and text == "":
                text = unquote(link)

            if link == '' and text == '':
                value = icon = u""
            # XXX: ???
            elif link == '' and text != '':
                value = text
                icon = u""
            else:  # link and text given
                if new_window:
                    value = u'<a href="{}" target="_blank" title="{}">{}</a>'.format(link, t(language, 'show in new window'), text)
                else:
                    value = u'<a href="{}">{}</a>'.format(link, text)
            if icon != "":
                value += u'<img src="{}"/>'.format(icon)

            return (metafield.getLabel(), value)
        except:
            logg.exception("exception in getFormattedValue, error getting formatted value for URI")
            return (metafield.getLabel(), "")

    def format_request_value_for_db(self, field, params, item, language=None):
        uri = params.get(item)
        quoted_uri = quote_uri(uri)
        linktext = params.get(item + "_text").replace(u";", u"\u037e")
        if not quoted_uri:
            return ""
        if not linktext:
            # don't add a single ';' add the end of the url (quoted_uri)
            return u"{}".format(quoted_uri)
        return u"{};{}".format(quoted_uri, linktext)

    def get_metafieldeditor_html(self, fielddata, metadatatype, language):
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

    def parse_metafieldeditor_settings(self, data):
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
