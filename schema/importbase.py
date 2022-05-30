# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
from . import schema

logg = logging.getLogger(__name__)


class ImportException(Exception):
    pass


class NoMappingFound(ImportException):

    def __init__(self, msg="Error", typ=""):
        if typ:
            msg = u"{} (type '{})'".format(msg, typ)
        ImportException.__init__(self, msg)
        self.typ = typ


def get_all_import_mappings(mapping_type):
    mapping_name = mapping_type + "mapping"
    types = {}
    ambiguous_types = {}
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
            logg.error("ambiguous mapping for bibtex type '%s': %s - choosing last one", typ, metatype_names[-1])
            ambiguous_types[typ] = metatype_names
            types[typ] = metatype_names[-1]
    return types, ambiguous_types


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
        logg.error("ambiguous mapping for %s type '%s': %s - choosing last one", mapping_type, mapped_type, mappings[-1])
        return mappings[-1]
    else:
        return mappings[0]
