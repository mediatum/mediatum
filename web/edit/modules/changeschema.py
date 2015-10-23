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

from core.acl import AccessData
from schema.schema import loadTypesFromDB
from core.translation import translate
from core.transition import httpstatus, current_user
from utils.utils import dec_entry_log
from core import Node
from contenttypes import Data
from core import db

q = db.query
logg = logging.getLogger(__name__)


def elemInList(list, name):
    for item in list:
        if item.__name__.lower() == name:
            return True
    return False


def getTypes(datatypes):
    res = []
    for dtype in datatypes:
        if dtype.name not in [
                "root",
                "user",
                "usergroup",
                "home",
                "mapping",
                "collections",
                'metadatatype',
                'metafield',
                'mask',
                'searchmaskitem',
                'mappingfield',
                'shoppingbag',
                'maskitem'] and not dtype.__name__.lower().startswith("workflow"):
            res.append(dtype)
    return res


def getContainers(datatypes):
    res = []
    datatypes = getTypes(datatypes)
    for dtype in datatypes:
        if hasattr(dtype, "isContainer"):
            if dtype.isContainer():
                res.append(dtype)
    db.session.commit()
    return res


@dec_entry_log
def getContent(req, ids):
    user = current_user
    node = q(Node).get(ids[0])
    if not node.has_write_access() or "changeschema" in current_user.hidden_edit_functions:
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    error = req.params.get("error")

    schemes = [scheme for scheme in AccessData(req).filter(loadTypesFromDB()) if scheme.isActive()]
    long_scheme_names = {scheme.name: scheme.getLongName() for scheme in schemes}

    # find allowed datatypes
    dtypes = []
    datatypes = Data.get_all_datatypes()
    for scheme in schemes:
        for dtype in scheme.getDatatypes():
            if dtype not in dtypes:
                for t in datatypes:
                    if t.__name__.lower() == dtype and not elemInList(dtypes, t.__name__.lower()):
                        dtypes.append(t)

    dtypes.sort(key=lambda x: translate(x.__name__, request=req).lower())

    admissible_objtypes = getTypes(datatypes)
    admissible_datatypes = [n for n in admissible_objtypes if n.getCategoryName() in ['document',
                                                                                      'image',
                                                                                      'video',
                                                                                      'audio']]
    admissible_containers = [n for n in admissible_objtypes if n.getCategoryName() in ['container']]

    admissible_objtypes.sort(key=lambda x: translate(x.__name__, request=req).lower())
    admissible_datatypes.sort(key=lambda x: translate(x.__name__, request=req).lower())
    admissible_containers.sort(key=lambda x: translate(x.__name__, request=req).lower())

    available_schemes = [s for s in schemes if node.type in s.getDatatypes()]

    # filter schemes for special datatypes
    if req.params.get("objtype", "") != "":
        new_type = req.params.get('objtype', '')
        new_schema = req.params.get('schema', '')

        schemes = [scheme for scheme in schemes if new_type in scheme.getDatatypes()]

        if new_type != node.type or new_schema != node.schema:
            logg.info("{} changed node schema for node {} '{}' from '{}' to '{}'".format(user.login_name,
                                                                                         node.id,
                                                                                         node.name,
                                                                                         node.type,
                                                                                         new_type))
            #
            node.type = new_type
            node.schema = new_schema
            db.session.commit()
            # you must remove the node reference otherwise the sqlalchemy object
            # has the wrong class manager and throws an exception when accessing
            # the object
            del node
            node = q(Node).get(req.params.get('id'))
            available_schemes = [s for s in schemes if new_type in s.getDatatypes()]

    if "action" in req.params.keys():
        if req.params.get("action").startswith("get_schemes_for_"):
            new_type = req.params.get("action").replace("get_schemes_for_", "").lower()
            available_schemes = [s for s in schemes if new_type in s.getDatatypes()]

            req.writeTAL("web/edit/modules/changeschema.html",
                         {'schemes': available_schemes,
                          'current_schema': node.schema},
                         macro="changeschema_selectscheme")
        return ""

    containers = getContainers(datatypes)

    d = {'id': req.params.get('id'),
         'error': error,
         'node': node,
         'current_type': node.type,
         'current_schema': node.schema,
         'category_name': node.getCategoryName(),
         'type_alias': node.getTypeAlias(),
         'is_container': int(node.isContainer()),
         'nodes': [node]}

    if not node.isContainer():
        d['long_current_schema'] = long_scheme_names[node.schema]

    if node.type in [dtype.__name__.lower() for dtype in containers]:
        d['schemes'] = []
        d['datatypes'] = admissible_containers  # containers
    else:
        d['schemes'] = available_schemes
        d['datatypes'] = admissible_datatypes  # dtypes

    return req.getTAL("web/edit/modules/changeschema.html", d, macro="changeschema_popup")
