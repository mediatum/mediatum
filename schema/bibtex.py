# coding=utf8

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

""" We want to parse even badly broken bibtex files, no longer adhering to
    the "official" bibtex grammar. In particular, we need to handle
    curly brace misleveling, missing quotation marks, missing attributes,
    missing ids, etc.
    Hence, we don't use a lex+yacc approach but rather a heuristic approach,
    which extracts records from the source file only by looking into
    "@doctype" records and "field = " fields, ignoring all in between (and
    not dealing with curly braces at all)
"""

from __future__ import division
from __future__ import print_function

import datetime as _datetime
import json as _json
import os as _os
import os.path as _
import re
import sys
import codecs
import logging
import unicodedata
import string as _string
import time

import backports as _backports
import backports.functools_lru_cache as _
from bibtexparser import load as bibtex_load
from bibtexparser.bparser import BibTexParser
import bibtexparser.customization
import ruamel as _ruamel
import ruamel.yaml as _

import core as _core
import schema as _schema
from core.database.postgres.node import Node
from .schema import Metadatatype
from contenttypes.document import Document
from utils.date import parse_date

logg = logging.getLogger(__name__)

token = re.compile(r'@\w+\s*{\s*|[a-zA-Z-_]+\s*=\s*{?["\'{]|[a-zA-Z-]+\s*=\s+[0-9a-zA-Z_]')
comment = re.compile(r'%[^\n]*\n')
delim = re.compile(r'\W')
delim2 = re.compile(r'^(?u)\s*[\w+_\-\:]*\s*\,')
frontgarbage = re.compile(r'^\W*', re.UNICODE)
backgarbage = re.compile(r'[ \n\t}"\',]*$')
xspace = re.compile(r'\s+')


counterpiece = {"{": "}", '"': '"', "'": "'"}


class MissingMapping(Exception):

    def __init__(self, message=""):
        self.message = message

    def __str__(self):
        return self.message


def getNow():
    now = _datetime.datetime.now().isoformat()
    now = now.replace('T', '_').replace(':', '-')
    now = now.split('.')[0]
    return now


@_backports.functools_lru_cache.lru_cache()
def get_document_type_fields():
    with open(_os.path.normpath(_os.path.join(__file__, "..", "bibtex-article-types.yaml")), "rb") as f:
        document_types = _ruamel.yaml.YAML(typ="safe", pure=True).load(f)
    for fields in document_types.itervalues():
        assert not frozenset(fields["required"]).intersection(fields["optional"])
    return document_types


def getbibtexmappings():
    bibtextypes = {}
    for metatype in _schema.loadTypesFromDB():
        for bibtextype in metatype.get("bibtexmapping").split(";"):
            if bibtextype:
                metatype_name = metatype.getName()
                bibtextypes[bibtextype] = bibtextypes.get(bibtextype, []) + [metatype_name]
    for bibtextype in bibtextypes:
        if len(bibtextypes[bibtextype]) == 1:
            bibtextypes[bibtextype] = bibtextypes[bibtextype][-1]
        elif len(bibtextypes[bibtextype]) > 1:
            logg.error("bibtex import: ambiguous mapping for bibtex type '%s': %s - choosing last one",
                bibtextype, bibtextypes[bibtextype])
            bibtextypes[bibtextype] = bibtextypes[bibtextype][-1]
    return bibtextypes


def _detecttype(doctype, fields):
    results = []
    for bibname, fields in get_document_type_fields().iteritems():
        score = 0
        if doctype.lower() == bibname.lower():
            score += 120
        score -= len(fields["required"])
        for field in fields["required"]:
            if field in fields:
                score += 20
        for field in fields["optional"]:
            if field in fields:
                score += 10
        results += [(score, bibname)]
    if not results:
        # no mapping types defined
        raise ValueError("no bibtex mappings defined")
    score, bibname = max(results)

    if score >= 30:
        return bibname
    else:
        return None


def _bibteximport_customize(record):
    """
    Sanitize bibtex records (unicode, name lists).
    """
    record = bibtexparser.customization.convert_to_unicode(record)
    record = bibtexparser.customization.author(record)
    record = bibtexparser.customization.editor(record)
    # editor function adds "ids" (s.th. like hashes), we don't need them
    if record.get("editor"):
        record["editor"] = list(v["name"] for v in record["editor"])
    # convert author/editor lists into semicolon-separated strings
    for key in ("author", "editor"):
        if key in record:
            record[key] = ";".join(", ".join(n for n in name.split(", ") if n.strip()) for name in record[key])
    for key in ("title", "booktitle"):
        if key in record:
            record[key] = record[key].replace('\n', ' ')
    return record


def getentries(filepath):
    parser = BibTexParser(common_strings=True)
    # accept also non standard records like @SCIENCEREPORT
    parser.ignore_nonstandard_types = False
    parser.customization = _bibteximport_customize
    # use utf-8-sig instead of utf-8 to get rid of BOM_UTF8, which confuses bibtex parser
    for encoding in ('utf-8-sig', 'utf-16', None):
        try:
            with codecs.open(filepath, "r", encoding=encoding) as fi:
                bibtex = bibtex_load(fi, parser=parser)
        except UnicodeError as exc:
            error = exc
        except Exception as exc:
            error = exc
            break
        else:
            # seems to be the correct encoding, don't try other encodings
            return bibtex.entries
    logg.error("bibtex import: bibtexparser failed: %s", error)
    raise ValueError("bibtex_unspecified_error")


def importBibTeX(entries, node, creator=None):
    if creator:
        logg.info("bibtex import: import started by user '%s'", creator)
    else:
        logg.info("bibtex import: starting import (%s)", ustr(sys.argv))

    bibtextypes = getbibtexmappings()

    logg.info("bibtex import: %d entries", len(entries))

    for fields in entries:
        entry_key = fields[u"key"] = fields.pop("ID")
        metadatatype = _detecttype(fields.pop("ENTRYTYPE"), fields)
        if not metadatatype:
            continue
        if metadatatype not in bibtextypes:
            raise MissingMapping(metadatatype)
        metadatatype = _core.db.query(Metadatatype).filter_by(name=bibtextypes[metadatatype]).one()
        mappingfields = {}
        metadatafields = {}
        dateformats = {}

        # check for mask configuration
        mask = metadatatype.get_mask("import-bibtex")
        if not mask:
            logg.warning("bibtex import: no 'import-bibtex' mask found, importing without mapping")
        for maskitem in (mask.all_maskitems if mask else ()):
            try:
                mappingfield = _core.db.query(Node).get(maskitem.get(u"mappingfield"))
                metadatafield = _core.db.query(Node).get(maskitem.get(u"attribute"))
                # force AttributeError if those objects weren't found in DB:
                mappingfield.name
                metadatafield.name
            except AttributeError as error:
                logg.error(
                        "bibtex import docid='%s': field error for bibtex mask for type %s and bibtex-type '%s': %s",
                        entry_key,
                        metadatatype.name,
                        metadatatype.get("bibtexmapping"),
                        error,
                       )
            else:
                if metadatafield.get(u"type") == u"date":
                    dateformats[metadatafield.name] = metadatafield.metatype_data["format"]
                mappingfields[mappingfield.name] = mappingfield
                metadatafields[mappingfield.name] = metadatafield

        doc = Document(entry_key, schema=metadatatype.name)
        for fieldname, fieldvalue in fields.iteritems():
            if fieldname in metadatafields:
                fieldname = metadatafields[fieldname].name
            value = fieldvalue
            if fieldname in dateformats:  # format date field
                value = str(parse_date(value, dateformats[fieldname]))
                # if date format does not contains '%' the valid digit of the result must not be longer than the date format
                # e.g. if dateformats[fieldname] is 'yyyy' then the result value must be clipped after 4 characters
                # afterwards the result is expanded again (without the invalid digits)
                if "%" not in dateformats[fieldname]:
                    value = value[:len(dateformats[fieldname])]
                    value = str(parse_date(value, dateformats[fieldname]))

            # value must not be changed if 'exportformat' is empty
            if fieldname in mappingfields and mappingfields[fieldname].get('exportformat'):
                value = _schema.getMetadataType("mappingfield").evaluate_square_brackets(
                        mappingfields[fieldname].get('exportformat'),
                        metadatafields[fieldname],
                        mask,
                        fieldname,
                        value=_json.dumps(dict(raw=fieldvalue,cooked=value)),
                       )

            doc.set(fieldname, value)

        # because the bibtex import contains only a subset of the metadata defined in metadatatype,
        # all other metadata are created and set to default values.
        # this will be done in the same manner as if the document is loaded in editor and saved without
        # any changes (required fields are not considered)
        editmask = metadatatype.get_mask(u"editmask")
        if editmask:
            editmask.set_default_metadata(doc)

        try:
            node.children.append(doc)
            if creator is not None:
                doc.set("creator", creator)
            doc.set("creationtime", unicode(time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
        except Exception as e:
            logg.exception("bibtex exception")
            raise ValueError()

    logg.debug("bibtex import: finished import")
