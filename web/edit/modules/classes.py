# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

import core.nodecache as _core_nodecache
import core.translation as _core_translation
from core.users import user_from_session as _user_from_session
from core import httpstatus

from core.database.postgres.node import Node
from core import db
import web.edit.edit_common as _web_edit_edit_common

q = db.query
def getInformation():
    return {"version": "1.1", "system": 0}


def getContent(req, ids):
    user = _user_from_session()
    if not all(q(Node).get(nid).has_write_access() for nid in ids) or "classes" in user.hidden_edit_functions:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    writable_container_parent_nids = _web_edit_edit_common.get_writable_container_parent_nids(user)

    return _tal.processTAL(
            dict(
                basedirs=[_core_nodecache.get_home_root_node(), _core_nodecache.get_collections_node()],
                script="var currentitem = '{0}';\nvar currentfolder = '{0}';\nvar nids = '{1}';".format(
                        ','.join(map(str,tuple(writable_container_parent_nids)+(req.values.get("id", _core_nodecache.get_root_node().id),))),
                        ','.join(map(str, writable_container_parent_nids)),
                    ),
                idstr=",".join(ids),
                node_count=len(ids),
                translate=_core_translation.translate,
                language=_core_translation.set_language(req.accept_languages),
            ),
            file="web/edit/modules/classes.html",
            macro="classtree",
            request=req,
        )
