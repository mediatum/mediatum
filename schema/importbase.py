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

import logging
from . import schema

logg = logging.getLogger("backend")

class ImportException(Exception):
    pass


class NoMappingFound(ImportException):
    def __init__(self, msg="Error", typ=""):
        if typ:
            msg = "{} for type '{}'".format(msg, typ)
        ImportException.__init__(self, msg)
        self.typ = typ


def get_all_import_mappings(mapping_type):
    mapping_name = mapping_type + "mapping"
    types = {}
    # find all mappings
    for metatype in schema.loadTypesFromDB():
        for typ in metatype.get(mapping_name).split(";"):
            if typ:
                metatype_name = metatype.getName()
                types.setdefault(typ, []).append(metatype_name)
    # mappings should be unique, check
    for typ, metatype_names in types.iteritems():
        if len(metatype_names) == 1:
            types[typ] = metatype_names[0]
        else:
            logg.error("ambiguous mapping for bibtex type '%s': %s - choosing last one" % (typ, metatype_names[-1]))
            types[typ] = metatype_names[-1]
    return types


def get_import_mapping(mapping_type, mapped_type):
    mapping_name = mapping_type + "mapping"
    mappings = []
    # search all mappings for mapped_type
    for metatype in schema.loadTypesFromDB():
        for typ in metatype.get(mapping_name).split(";"):
            if typ == mapped_type:
                mappings.append(metatype.getName())
    # mapping should be unique
    if not mappings:
        return None
    elif len(mappings) > 1:
        logg.error("ambiguous mapping for %s type '%s': %s - choosing last one" % (mapping_type, mapped_type, mappings[-1]))
        return mappings[-1]
    else:
        return mappings[0]
