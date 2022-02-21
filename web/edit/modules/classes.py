# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

import core.nodecache as _core_nodecache
import core.translation as _core_translation
from core.users import user_from_session as _user_from_session
from core import httpstatus
from core import Node
from core import db

q = db.query
def getInformation():
    return {"version": "1.1", "system": 0}


def getContent(req, ids):
    user = _user_from_session()
    nodes = []
    for nid in ids:
        node = q(Node).get(nid)
        if not node.has_write_access():
            req.response.status_code = httpstatus.HTTP_FORBIDDEN
            return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)
        nodes.append(node)

    if "classes" in user.hidden_edit_functions:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    return _tal.processTAL(
            dict(
                basedirs=[_core_nodecache.get_home_root_node(), _core_nodecache.get_collections_node()],
                script="var currentitem = '{0}';\nvar currentfolder = '{0}'".format(
                        req.params.get("id", _core_nodecache.get_root_node().id),
                    ),
                idstr=",".join(ids),
                nodes=nodes,
                t=_core_translation.t,
                language=_core_translation.set_language(req.accept_languages),
            ),
            file="web/edit/modules/classes.html",
            macro="classtree",
            request=req,
        )
