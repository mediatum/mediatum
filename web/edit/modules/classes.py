# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

import core.translation as _core_translation
from core.users import user_from_session as _user_from_session
from core import httpstatus
from core import Node
from core.systemtypes import Root
from contenttypes import Collections, Home
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

    v = {}
    v["basedirs"] = [q(Home).one(), q(Collections).one()]
    nid = req.params.get("id", q(Root).one().id)
    v["script"] = "var currentitem = '%s';\nvar currentfolder = '%s'" % (nid, nid)
    v["idstr"] = ",".join(ids)
    v["nodes"] = nodes
    v["t"] = _core_translation.t
    v["language"] = _core_translation.lang(req)
    return _tal.processTAL(v, file="web/edit/modules/classes.html", macro="classtree", request=req)
