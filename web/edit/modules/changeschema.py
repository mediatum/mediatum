"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Werner Neudenberger <neudenberger@ub.tum.de>
 Copyright (C) 2010 Matthias Kramm Neudenberger <kramm@in.tum.de>
 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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

from schema.schema import get_permitted_schemas
from core.translation import translate
from core.transition import httpstatus, current_user
from utils.utils import dec_entry_log
from core import Node
from contenttypes import Data, Content, Container
from core import db

q = db.query
logg = logging.getLogger(__name__)


def _redirect_to_view(req):
    req["Location"] = "{}?id={}&tab=changeschema".format(req.fullpath, req.args["id"])
    return httpstatus.HTTP_MOVED_TEMPORARILY


@dec_entry_log
def getContent(req, ids):
    user = current_user
    node = q(Node).get(ids[0])
    if not node.has_write_access() or "changeschema" in current_user.hidden_edit_functions:
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    error = req.params.get("error")

    schemes = get_permitted_schemas()
    long_scheme_names = {scheme.name: scheme.getLongName() for scheme in schemes}


    if isinstance(node, Container):
        admissible_containers = [s.__name__.lower()
                                 for s
                                 in Container.get_all_subclasses(filter_classnames=["container", "collections", "home", "root"])]
    else:
        admissible_content_types = [s.__name__.lower()
                                    for s
                                    in Content.get_all_subclasses(filter_classnames=["content"])]

    # filter schemes for special datatypes
    if req.params.get("objtype", "") != "":
        new_type = req.params.get('objtype', '')
        new_schema = req.params.get('schema', '')

        if not new_schema:
            return _redirect_to_view(req)

        if new_type != node.type or new_schema != node.schema:


            if isinstance(node, Container):
                if not new_type in admissible_containers:
                    logg.warn(u"changeschema: illegal container type %s", new_type)
                    return httpstatus.HTTP_BAD_REQUEST
            else:
                if not new_type in admissible_content_types:
                    logg.warn(u"changeschema: illegal content type %s", new_type)
                    return httpstatus.HTTP_BAD_REQUEST

            available_schema_names = [s.name for s in schemes if new_type in s.getDatatypes()]

            if not new_schema in available_schema_names:
                    logg.warn(u"changeschema: illegal schema %s", new_schema)
                    return httpstatus.HTTP_BAD_REQUEST

            logg.info(u"{} changed node schema for node {} '{}' from '{}' to '{}'".format(user.login_name,
                                                                                         node.id,
                                                                                         node.name,
                                                                                         node.type,
                                                                                         new_type))
            node.type = new_type
            node.schema = new_schema

            db.session.commit()

            return _redirect_to_view(req)

    elif "action" in req.params.keys():
        available_schemes = [s for s in schemes if node.type in s.getDatatypes()]
        if req.params.get("action").startswith("get_schemes_for_"):
            new_type = req.params.get("action").replace("get_schemes_for_", "").lower()
            available_schemes = [s for s in schemes if new_type in s.getDatatypes()]

            req.writeTAL("web/edit/modules/changeschema.html",
                         {'schemes': available_schemes,
                          'current_schema': node.schema},
                         macro="changeschema_selectscheme")
        return ""

    else:
        d = {'id': req.params.get('id'),
             'error': error,
             'node': node,
             'current_type': node.type,
             'current_schema': node.schema,
             # XXX: this is the only line that uses getTypeAlias. What is the real meaning?
             'type_alias': node.getTypeAlias(),
             'is_container': int(node.isContainer()),
             'nodes': [node]}

        d['long_current_schema'] = long_scheme_names.get(node.schema)

        available_schemes = [s for s in schemes if node.type in s.getDatatypes()]

        if isinstance(node, Container):
            admissible_containers.sort(key=lambda x: translate(x, request=req).lower())
            d['schemes'] = available_schemes
            d['datatypes'] = admissible_containers
        else:
            admissible_content_types.sort(key=lambda x: translate(x, request=req).lower())
            d['schemes'] = available_schemes
            d['datatypes'] = admissible_content_types

        return req.getTAL("web/edit/modules/changeschema.html", d, macro="changeschema_popup")
