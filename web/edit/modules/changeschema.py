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
import core.users as users

import core.acl as acl
import logging

from core.acl import AccessData
from schema.schema import loadTypesFromDB
from core.translation import translate
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
    user = users.getUserFromRequest(req)
    node = q(Node).get(ids[0])
    access = acl.AccessData(req)
    if not access.hasWriteAccess(node) or "changeschema" in users.getHideMenusForUser(user):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    error = req.params.get("error")
    currentContentType = node.type

    if "/" in node.type:
        currentSchema = node.type.split('/')[1]
    else:
        currentSchema = ''

    currentCategoryName = node.getCategoryName()
    currentTypeAlias = node.getTypeAlias()

    schemes = AccessData(req).filter(loadTypesFromDB())
    _schemes = []
    for scheme in schemes:
        if scheme.isActive():
            _schemes.append(scheme)
    schemes = _schemes

    schemeNames2LongNames = {'': ''}
    for s in schemes:
        schemeNames2LongNames[s.getName()] = s.getLongName()

    try:
        currentSchemaLongName = schemeNames2LongNames[currentSchema]
    except KeyError:
        currentSchemaLongName = ''

    # find out which schema allows which datatype, and hence,
    # which overall data types we should display
    dtypes = []
    datatypes = Data.get_all_datatypes()
    for scheme in schemes:
        for dtype in scheme.getDatatypes():
            if dtype not in dtypes:
                for t in datatypes:
                    if t.__name__.lower() == dtype and not elemInList(dtypes, t.__name__.lower()):
                        dtypes.append(t)

    #todo: sorting needs to be fixed
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

    available_schemes = [
        s for s in schemes if currentContentType in s.getDatatypes()]

    # filter schemes for special datatypes
    if req.params.get("objtype", "") != "":
        _schemes = []
        for scheme in schemes:
            if req.params.get("objtype", "") in scheme.getDatatypes():
                _schemes.append(scheme)
        schemes = _schemes
        schemes.sort(key=lambda x: translate(x.getLongName(), request=req).lower())

        newObjectType = req.params.get("objtype")
        newSchema = req.params.get("schema")
        if not newSchema:
            newSchema = ''

        newType = newObjectType
        if newSchema:
            newType += '/' + newSchema

        oldType = currentContentType
        if currentSchema:
            oldType = oldType + '/' + currentSchema

        if newType != oldType:
            node.type = newType
            logg.info("%s changed node schema for node %s '%s' from '%s' to '%s'", user.name, node.id, node.name, oldType, newType)

            node = q(Node).get(node.id)

            currentContentType = node.type
            currentSchema = newSchema
            currentSchemaLongName = schemeNames2LongNames[currentSchema]
            currentCategoryName = node.getCategoryName()
            currentTypeAlias = node.getTypeAlias()
            available_schemes = [
                s for s in schemes if newObjectType in s.getDatatypes()]

    isContainer = False
    if hasattr(node, "isContainer"):
        isContainer = node.isContainer()

    if "action" in req.params.keys():
        if req.params.get("action").startswith("get_schemes_for_"):
            newObjectType = req.params.get(
                "action").replace("get_schemes_for_", "")
            available_schemes = [
                s for s in schemes if newObjectType in s.getDatatypes()]
            req.writeTAL("web/edit/modules/changeschema.html",
                         {'schemes': available_schemes, 'currentSchema': currentSchema}, macro="changeschema_selectscheme")
        return ""

    containers = getContainers(datatypes)

    d = {'id': req.params.get('id'),
         'error': error,
         'node': node,
         'currentContentType': currentContentType,
         'currentSchema': currentSchema,
         'currentSchemaLongName': currentSchemaLongName,
         'currentCategoryName': currentCategoryName,
         'currentTypeAlias': currentTypeAlias,
         'isContainer': int(isContainer),
         'nodes': [node]}

    if currentContentType in [dtype.name for dtype in containers]:
        d['schemes'] = []
        d['datatypes'] = admissible_containers  # containers
    else:
        d['schemes'] = available_schemes
        d['datatypes'] = admissible_datatypes  # dtypes

    return req.getTAL("web/edit/modules/changeschema.html", d, macro="changeschema_popup")
