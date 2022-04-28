# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging

import mediatumtal.tal as _tal
from schema.schema import get_permitted_schemas
from core.translation import translate
from core.users import user_from_session as _user_from_session
from core import httpstatus
from core import Node
from contenttypes import Data, Content, Container
from core import db

q = db.query
logg = logging.getLogger(__name__)


def _redirect_to_view(req):
    req.response.location = "{}?srcnodeid={}&id={}&tab=changeschema".format(
            req.path,
            req.values.get("srcnodeid", ""),
            req.args["id"],
        )
    return httpstatus.HTTP_MOVED_TEMPORARILY


def getContent(req, ids):
    user = _user_from_session()
    node = q(Node).get(ids[0])
    if not node.has_write_access() or "changeschema" in user.hidden_edit_functions:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    # nobody should be able to change the type/schema of his home directory
    if node.id == user.home_dir_id:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

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
                    logg.warning(u"changeschema: illegal container type %s", new_type)
                    return httpstatus.HTTP_BAD_REQUEST
            else:
                if not new_type in admissible_content_types:
                    logg.warning(u"changeschema: illegal content type %s", new_type)
                    return httpstatus.HTTP_BAD_REQUEST

            available_schema_names = [s.name for s in schemes if new_type in s.getDatatypes()]

            if not new_schema in available_schema_names:
                    logg.warning(u"changeschema: illegal schema %s", new_schema)
                    return httpstatus.HTTP_BAD_REQUEST

            logg.info(
                    u"%s changed node schema for node %s '%s' from '%s' to '%s'",
                    user.login_name,
                    node.id,
                    node.name,
                    node.type,
                    new_type,
                )
            node.type = new_type
            node.schema = new_schema

            db.session.commit()

            return _redirect_to_view(req)

    elif "action" in req.params.keys():
        available_schemes = [s for s in schemes if node.type in s.getDatatypes()]
        if req.params.get("action").startswith("get_schemes_for_"):
            new_type = req.params.get("action").replace("get_schemes_for_", "").lower()
            available_schemes = [s for s in schemes if new_type in s.getDatatypes()]

            req.response.set_data(_tal.processTAL({'schemes': available_schemes, 'current_schema': node.schema},
                                                  file="web/edit/modules/changeschema.html",
                                                  macro="changeschema_selectscheme",
                                                  request=req))
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

        d["csrf"] = req.csrf_token.current_token
        d["srcnodeid"] = req.values.get("srcnodeid", "")
        return _tal.processTAL(d, file="web/edit/modules/changeschema.html", macro="changeschema_popup", request=req)
