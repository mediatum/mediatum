# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
from mediatumtal import tal

import core.nodecache as _core_nodecache
from core import httpstatus
from utils.utils import esc
from core.metatype import Metatype
from core import db

q = db.query
logg = logging.getLogger(__name__)


class m_treeselect(Metatype):

    name = "treeselect"

    def getEditorHTML(self, metafield, value="", width=40, lock=0, language=None, required=None):
        return tal.getTAL("metadata/treeselect.html", {"lock": lock,
                                                       "value": value,
                                                       "width": width,
                                                       "name": metafield.getName(),
                                                       "metafield": metafield,
                                                       "required": 1 if required else None,
                                                       },
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL(
                "metadata/treeselect.html",
                dict(name=context.name, value=context.value),
                macro="searchfield",
                language=context.language,
               )

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True, template_from_caller=None):
        value = node.get(metafield.getName())
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item)
        try:
            return value.replace("; ", ";")
        except:
            logg.exception("exception in format_request_value_for_db, returning value")
            return value


    # method for popup methods of type treeselect
    def getPopup(self, req):
        req.response.set_data(tal.processTAL(
                dict(
                    basedir=_core_nodecache.get_collections_node(),
                    name=req.params.get("name", ''),
                    value=req.params.get("value"),
                ),
                file="metadata/treeselect.html",
                macro="popup",
                request=req,
            ))
        req.response.status_code = httpstatus.HTTP_OK
        return httpstatus.HTTP_OK

    translation_labels = dict(
        de=dict(
            treeselect_popup_title="Knotenauswahl",
            fieldtype_treeselect="Knotenauswahlfeld",
            fieldtype_treeselect_desc="Feld zur Knotenauswahl mit Hilfe eins Baumes",
            treeselect_titlepopupbutton=u"Knotenauswahl öffnen",
            treeselect_done=u"Übernehmen",
        ),
        en=dict(
            treeselect_popup_title="Node selection",
            fieldtype_treeselect="node selection field",
            fieldtype_treeselect_desc="field for node selection using a tree",
            treeselect_titlepopupbutton="open node selection",
            treeselect_done="Done",
        ),
    )
