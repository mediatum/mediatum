# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import httplib as _httplib
import logging

from schema.schema import getMetadataType

from core import webconfig
from core import db
from core.database.postgres.node import Node
import core.translation as _core_translation
from web import frontend as _web_frontend

logg = logging.getLogger(__name__)
q = db.query

#
# help window for metadata field
#
def show_help(req):
    if req.values.get("maskid", "") != "":
        field = q(Node).get(req.values["maskid"])
    else:
        field = q(Node).get(req.values["id"])
    if field.has_read_access():
        html = webconfig.theme.render_macro(
                "popups.j2.jade",
                "show_help",
                dict(
                    field=field,
                    html_head_style_src=_web_frontend.html_head_style_src,
                    html_head_javascript_src=_web_frontend.html_head_javascript_src,
                ),
            )
        req.response.status_code = _httplib.OK
    else:
        html = _core_translation.translate(_core_translation.set_language(req.accept_languages), "permission_denied")
        req.response.status_code = _httplib.FORBIDDEN
    req.response.set_data(html)
#
# show attachmentbrowser for given node
# parameter: req.id, req.mediatum_contextfree_path
#


def show_attachmentbrowser(req):
    node = q(Node).get(req.values["id"])
    version_id = req.args.get("v")
    if version_id:
        node = node.get_tagged_version(unicode(version_id))
    if not node.has_data_access():
        req.response.set_data(_core_translation.translate(
                _core_translation.set_language(req.accept_languages),
                "permission_denied",
            ))
        req.response.status_code = _httplib.FORBIDDEN
        return

    from core.attachment import getAttachmentBrowser
    getAttachmentBrowser(node, req)
# use popup method of  metadatatype
def popup_metatype(req):
    mtype = getMetadataType(req.mediatum_contextfree_path.split("/")[-1])
    if mtype and hasattr(mtype, "getPopup"):
        mtype.getPopup(req)
    else:
        logg.error("error, no popup method found")
