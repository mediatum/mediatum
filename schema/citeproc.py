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
"""
import citeproc metadata in CSL, JSON variant as served by dx.doi.org.
"""

from collections import defaultdict
import json
import logging
from pprint import pprint
import requests
import datetime

from core import tree
from schema import getMetaType
from . import importbase
from .importbase import NoMappingFound

DX_DOI_URL = "http://dx.doi.org/"
logg = logging.getLogger("frontend")


class CSLField(object):
    def __init__(self, fieldtype):
        self.fieldtype = fieldtype


# CSL support special field types "name", "date" or "number". 
# Other fields are "standard"
# Missing fields are assumed to be "standard"
# see http://citationstyles.org/downloads/specification.html#appendix-iv-variables
FIELDS = defaultdict(lambda: CSLField("standard"), {
        # name fields
        "author": CSLField("name"), 
        "collection-editor": CSLField("name"), 
        "composer": CSLField("name"), 
        "container-author": CSLField("name"), 
        "director": CSLField("name"), 
        "editor": CSLField("name"), 
        "editorial-director": CSLField("name"), 
        "illustrator": CSLField("name"), 
        "interviewer": CSLField("name"), 
        "original-author": CSLField("name"), 
        "recipient": CSLField("name"), 
        "reviewed-author": CSLField("name"), 
        "translator": CSLField("name"), 
        # date fields
        "accessed": CSLField("date"), 
        "container": CSLField("date"), 
        "event-date": CSLField("date"), 
        "issued": CSLField("date"), 
        "original-date": CSLField("date"), 
        "submitted": CSLField("date"), 
        # number fields
        "chapter-number": CSLField("number"), 
        "collection-number": CSLField("number"), 
        "edition": CSLField("number"), 
        "issue": CSLField("number"), 
        "number": CSLField("number"), 
        "number-of-pages": CSLField("number"), 
        "number-of-volumes": CSLField("number"), 
        "volume": CSLField("number"), 
    }
)

# see http://citationstyles.org/downloads/specification.html#appendix-iii-types
TYPES = ["article", 
         "article-magazine",
         "article-newspaper",
         "article-journal",
         "bill",
         "book",
         # ...
         "dataset",
         # ...
         "paper-conference",
         # ...
         "report",
         # ...
         "thesis",
         "treaty",
         "webpage"
]        

class DOINotFound(Exception):
    pass


def check_mappings():
    s = importbase.get_all_import_mappings("citeproc")
    for typ in TYPES:
        if typ not in s:
            print typ, "is not associated with any metatype"
        else:
            print typ, "->", s[typ]


def convert_csl_date(date_value):
    '''Take date in CSL format and return a python date object.
    Date fields consist of "date-parts", in the order year -> month -> day.
    Day or day and month can be missing.
    '''
    # XXX: ranges?
    d = date_value["date-parts"][0]
    year = int(d[0])
    month = int(d[1]) if len(d) > 1 else 1
    day = int(d[2]) if len(d) > 2 else 1
    return datetime.date(year, month, day)


def convert_csl_names(names):
    '''Convert CSL names to 'family1, given1, suffix1;family2, given2, suffix2;(...)' style.
    Name fields can contain multiple names.
    '''
    res = []
    for n in names:
        parts = (n.get("family"), n.get("given"), n.get("suffix"))
        formatted = ", ".join([p.encode("utf8") for p in parts if p])
        res.append(formatted)
    return ";".join(res)

    
def get_citeproc_json(doi):
    """Get record for a given DOI in citeproc JSON format.
    :raises: DOINotFound if DOI is unknown to the server
    
    TODO: maybe there are other ways this can fail?
    """
    headers = {"Accept": "application/citeproc+json"}
    try:
        record = requests.get(DX_DOI_URL + doi, headers=headers).json()
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
    if typ not in TYPES:
        raise NoMappingFound("Not supported", typ)
    metatype_name = importbase.get_import_mapping("citeproc", typ)
    if not metatype_name: 
        raise NoMappingFound("No citeproc schema mapping could be found", typ)
    metatype = getMetaType(metatype_name)
    mask = metatype.getMask("citeproc")
    contenttype = "document"
    node = tree.Node(doi, contenttype + "/" + metatype_name)
    
    def get_converted_from_csl_record(key):
        value = record.get(key)
        if value is None:
            return None
        if FIELDS[key].fieldtype == "date":
            return convert_csl_date(value)
        elif FIELDS[key].fieldtype == "name":
            return convert_csl_names(value)
        elif FIELDS[key].fieldtype == "number":
            return int(value)
        else:
            return value.encode("utf8")
    
    for f in mask.getMaskFields():
        try:
            csl_name = "not defined"
            mfield = "not defined"
            med_name = "not defined"
            csl_name = tree.getNode(f.get("mappingfield")).getName()
            mfield = tree.getNode(f.get("attribute"))
            med_name = mfield.getName()
        except tree.NoSuchNodeError:
            msg = "citeproc import doi='{}': field error for citeproc mask for type '{}' and " \
            "csl-type '{}' csl_name='{}', mfield='{}', med_name='{}'".format(doi, metatype_name, typ, csl_name, mfield, med_name)
            logg.error(msg, exc_info=1)
            continue

        value = get_converted_from_csl_record(csl_name)
        if value is not None:
            node.set(med_name, value)

    target.addChild(node)
    node.setDirty()
    return node
