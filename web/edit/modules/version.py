# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
editor module for version handling
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange


import logging
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
import core.translation as _core_translation
from utils.date import format_date
from core import httpstatus
from core import Node, db
from core.users import user_from_session

q = db.query
logg = logging.getLogger(__name__)


def getContent(req, ids):
    user = user_from_session()
    userdir = user.home_dir

    if "metadata" in user.hidden_edit_functions:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    nid, = ids
    node = q(Node).get(nid)
    if not node.has_write_access() or node is userdir:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    idstr = ",".join(ids)

    logg.info("%s in editor version: %r", user.login_name, (node.id, node.name, node.type))

    if req.form.get('generate_new_version'):
        # Create new node version
        comment = req.form.get('version_comment', '')

        with node.new_tagged_version(comment=comment, user=user):
            node.attrs["updatetime"] = format_date()
        db.session.commit()
        logg.debug("%s create version %s", user.login_name, idstr)

    # version handling
    current_version = node.versions[-1]
    tagged_node_versions = node.tagged_versions.all()
    published_version = node.get_published_version()

    # context default for TAL interpreter
    ctx = dict(
        idstr=idstr,
        node=node,
        language=_core_translation.set_language(req.accept_languages),
        t=_core_translation.t,
        csrf=_core_csrfform.get_token(),
        untagged_current_version=current_version,
        published_version=published_version,
        srcnodeid=req.values.get("srcnodeid", ""),
        node_count=len(ids),
       )

    if tagged_node_versions:
        ctx["tagged_versions"] = tagged_node_versions[::-1] # descending version tag
        if current_version == tagged_node_versions[-1]:
            ctx["untagged_current_version"] = None
    else:
        ctx["tagged_versions"] = ()


    return _tal.processTAL(ctx, file="web/edit/modules/version.html", macro="create_version", request=req)
