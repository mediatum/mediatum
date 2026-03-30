# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
import citeproc metadata in CSL, JSON variant as served by dx.doi.org.
"""

from __future__ import division
from __future__ import print_function

from collections import defaultdict
import datetime
import itertools as _itertools
import json as _json
import logging
import os as _os
import os.path as _
import re

import backports as _backports
import backports.functools_lru_cache as _
import requests
import ruamel as _ruamel
import ruamel.yaml as _

import core as _core
import utils.utils as _utils_utils
from core.database.postgres.node import Node
from contenttypes import Document
import schema as _schema
from .schema import Metadatatype
from . import importbase
from .importbase import NoMappingFound

DX_DOI_URL = "http://dx.doi.org/"
logg = logging.getLogger(__name__)


@_backports.functools_lru_cache.lru_cache()
def _get_fields_for_types(typ):
    with open(_os.path.normpath(_os.path.join(__file__, "..", "citeproc-fields.yaml")), "rb") as f:
        fields = _ruamel.yaml.YAML(typ="safe", pure=True).load(f)
    total = tuple(_itertools.chain.from_iterable(fields.itervalues()))
    assert len(total) == len(frozenset(total))
    return frozenset(fields[typ])


# see http://citationstyles.org/downloads/specification.html#appendix-iii-types
CSL_TYPES = [
    'article',
    'article-magazine',
    'article-newspaper',
    'article-journal',
    'bill',
    'book',
    'book-chapter',
    'broadcast',
    'chapter',
    'dataset',
    '_default',
    'entry',
    'entry-dictionary',
    'entry-encyclopedia',
    'figure',
    'graphic',
    'interview',
    'legislation',
    'legal_case',
    'manuscript',
    'map',
    'misc',
    'motion_picture',
    'musical_score',
    '_null',
    'pamphlet',
    'paper-conference',
    'patent',
    'post',
    'post-weblog',
    'personal_communication',
    'report',
    'review',
    'review-book',
    'song',
    'speech',
    'thesis',
    'treaty',
    'webpage'
]

TYPES = [
    "_default",  # fallback type if no mapping is defined
    "_null",  # fallback type if type not given
    'journal-article',  # type not in CSL 1.0.1, but returned by dx.doi.org server
    'proceedings-article'  # type not in CSL 1.0.1, but returned by dx.doi.org server
] + CSL_TYPES

TYPE_SET = set(TYPES)

class DOINotFound(Exception):
    pass


class DOINotImported(Exception):
    pass


class InvalidDOI(Exception):
    pass


def convert_csl_date(date_value):
    '''Take date in CSL format and return a python date object.
    Date fields consist of "date-parts", in the order year -> month -> day.
    Day or day and month can be missing.
    '''
    # XXX: ranges?
    if "date-parts" in date_value:
        d = date_value[u"date-parts"][0]
        year = int(d[0])
        month = int(d[1]) if len(d) > 1 else 1
        day = int(d[2]) if len(d) > 2 else 1
        return datetime.date(year, month, day).isoformat()
    elif "raw" in date_value:
        raw_value = date_value[u"raw"]
        # XXX: we only support raw dates that consist of a single year at the moment
        try:
            year = int(raw_value)
            return datetime.date(year, 1, 1).isoformat()
        except:
            # well...
            logg.warning("unrecognized raw date string %s, returning it unchanged", raw_value)
            return raw_value


def convert_csl_names(names):
    '''Convert CSL names to 'family1, given1, suffix1;family2, given2, suffix2;(...)' style.
    Name fields can contain multiple names.
    '''
    res = []
    for n in names:
        parts = (n.get(u"literal"), n.get(u"family"), n.get(u"given"), n.get(u"suffix"))
        formatted = u", ".join([p for p in parts if p])
        res.append(formatted)
    return u";".join(res)


CSL_NUMBER_RE = re.compile(r"((\d+)\s*[-&]?\s*(\d+)$)|(\d+)(\s*,\s*(\d+))+$")


def check_number(number):
    """Checks if given arg is a 'number' as defined by the CSL specification.
    Numbers can be
    * 'real numbers': 23
    * ranges: 23 - 42
    * and: 23 & 42
    * list: 23,42
    """
    if CSL_NUMBER_RE.match(number) is None:
        return False
    else:
        return True


def get_citeproc_json(doi):
    """Get record for a given DOI in citeproc JSON format.
    :raises: DOIFound if DOI is unknown to the server
    :raises: DOINotImported if no valid metadata has been found for the DOI
    """
    headers = {"Accept": "application/citeproc+json"}
    res = requests.get(DX_DOI_URL + doi, headers=headers)
    if res.status_code == 404:
        raise DOINotFound()
    try:
        record = res.json()
    except ValueError:
        # invalid data returned
        raise DOINotImported()
    return record


DOI_RE = re.compile("(10[.].+/.+)", re.U)


def extract_and_check_doi(doi_or_uri):
    """Extract DOI if URL like http://dx.doi.org/10.01/test is given"""
    # simple case: starts with 10., treat it as doi
    if doi_or_uri.startswith("10.") and "/" in doi_or_uri:
        return doi_or_uri
    # try a regular expression match for other cases, like http
    match = DOI_RE.search(doi_or_uri)
    if match:
        return match.group(1)
    else:
        raise InvalidDOI()


def import_csl(record, target=None, name=None, testing=False):
    """Import data from a CSL record into a new node
    :param record: CSL record
    :type record: dict
    :param: target
    :type target: Node
    :param name: name for the new node. If none, try to get a unique id
        from the record (DOI) or generate an UUID.
    :raises: NoMappingFound if no mapping defined for the given type
    """
    typ = record[u"type"]
    if not typ:
        logg.warning("no type given in CSL import, using _null")
        typ = "_null"
    if typ not in TYPE_SET:
        logg.warning("unknown type %s given in CSL import, using _default", typ)
        typ = "_default"
    schema = importbase.get_import_mapping(u"citeproc", typ)
    if not schema:
        # no mapping, found, try fallback mapping
        schema = importbase.get_import_mapping(u"citeproc", u"_default")
        if not schema:
            # no _default defined, fail
            raise NoMappingFound("No citeproc schema mapping could be found", typ)
        logg.warning("no mapping found for type %s, using _default fallback mapping", typ)
    metatype = _core.db.query(Metadatatype).filter_by(name=schema).one()
    mask = metatype.getMask(u"import-citeproc")
    if not mask:
        raise NoMappingFound("target schema does not have a import-citeproc mask", typ)
    if name is None:
        name = record.get(u"DOI") or _utils_utils.gen_secure_token(128)
    node = Document(name, schema=schema)

    def get_converted_from_csl_record(key):
        value = record.get(key)
        if value is None:
            return None
        try:
            if key in _get_fields_for_types("date"):
                return convert_csl_date(value)
            elif key in _get_fields_for_types("name"):
                return convert_csl_names(value)
            elif key in _get_fields_for_types("number"):
                if not check_number(value):
                    logg.warning("field '%s' is of type number and contains an illegal value: '%s'!"
                              "See http://citationstyles.org/downloads/specification.html#number",
                              key, value)
                return unicode(value)
            elif isinstance(value, list):
                value = u''.join(value)
            # for standard fields which already are unicode objects
            return unicode(value)
        except:
            # all malformed input will be ignored
            # XXX: improve this when we know better what can happen...
            logg.exception("error while converting CSL field '%s' with value '%s', ignored", key, value)
            return u""

    for maskitem in mask.maskitems:
        try:
            mappingfield = _core.db.query(Node).get(int(maskitem[u"mappingfield"]))
            mfield = _core.db.query(Node).get(int(maskitem[u"attribute"]))
        except:
            logg.exception("citeproc import %r (%s): field error in maskitem %s (%s)",
                    name, typ, maskitem.id, maskitem.name)
            continue

        value = get_converted_from_csl_record(mappingfield.name)
        # fixes for special fields
        if mfield.get(u"type") == "url":
            value += u";Link"

        # get rid of month and day
        if mfield.name == u'year' and value is not None:
            value = value[0:4] + u'-00-00T00:00:00'

        # value must not be changed if 'exportformat' is empty
        if mappingfield.get('exportformat'):
            value = _schema.getMetadataType("mappingfield").evaluate_square_brackets(
                    mappingfield.get('exportformat'),
                    mfield,
                    mask,
                    mappingfield.name,
                    value=_json.dumps(dict(raw=record.get(mappingfield.name),cooked=value)),
                   )

        if value is not None:
            node.set(mfield.name, value)

    if target:
        target.content_children.append(node)

    # because the doi import contains only a subset of the metadata defined in metadatatype,
    # all other metadata are created and set to default values.
    # this will be done in the same manner as if the document is loaded in editor and saved without
    # any changes (required fields are not considered)
    editmask = metatype.get_mask(u"editmask")
    if editmask:
        editmask.set_default_metadata(node)

    return node


def import_doi(doi, target=None, name=None, testing=False):
    """Get record for a given DOI in citeproc JSON format and create a node from its information.
    :param doi:
    :param target:
    :type target: Node
    :raises: DOIFound if DOI is unknown to the server
    :raises: DOINotImported if no valid metadata has been found for the DOI
    """
    record = get_citeproc_json(doi)
    logg.debug("got citeproc data from server: %r", record)
    return import_csl(record, target, doi, testing=testing)
