# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2013 Tobias Stenzel <tobias.stenzel@tum.de>

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

import json
import logging
from pprint import pprint
import os.path
import requests

from core import tree
import importmapping

DX_DOI_URL = "http://dx.doi.org/"
logg = logging.getLogger("frontend")


class DOINotFound(Exception):
    pass

class NoMappingFound(Exception):
    pass

def get_citeproc_json(doi):
    """Get record for a given DOI in citeproc JSON format.
    :raises: DOINotFound if DOI is unknown to the server
    
    TODO: maybe there are other ways this can fail?
    """
    headers = {"Accept": "application/citeproc+json"}
    res = requests.get(DX_DOI_URL + doi, headers=headers).text
    try:
        record = json.loads(res)
    except ValueError:
        raise DOINotFound()
    return record


def import_doi(doi, target=None):
    """Get record for a given DOI in citeproc JSON format and create a node from its information.
    :raises: DOINotFound if DOI is unknown to the server
    """
    record = get_citeproc_json(doi)
    logg.debug("got citeproc data from server: %s", pprint(record))
    typ = record["type"]
    metatype = importmapping.get_import_mapping("csl", typ)
    if not metatype: 
        raise NoMappingFound("No schema mapping could be found for type " + typ)
    contenttype = "document"
    node = tree.Node(doi, contenttype + metatype)
    target.addChild(node)
    node.setDirty()
    return node
