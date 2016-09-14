# coding=utf8
"""
 mediatum - a multimedia content repository

 Copyright (C) 2008 Matthias Kramm <kramm@in.tum.de>

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

""" We want to parse even badly broken bibtex files, no longer adhering to
    the "official" bibtex grammar. In particular, we need to handle
    curly brace misleveling, missing quotation marks, missing attributes,
    missing ids, etc.
    Hence, we don't use a lex+yacc approach but rather a heuristic approach,
    which extracts records from the source file only by looking into
    "@doctype" records and "field = " fields, ignoring all in between (and
    not dealing with curly braces at all)
"""

import re
import os
import shutil
import sys
import codecs
import logging
import unicodedata

from bibtexparser import load as bibtex_load
from bibtexparser.bparser import BibTexParser
import bibtexparser.customization

from core import db, Node
from .schema import Metadatatype
import core.users as users
from contenttypes import Directory
from contenttypes.document import Document
from utils.utils import u, u2, utf8_decode_escape
from utils.date import parse_date

q = db.query


logg = logging.getLogger(__name__)

ESCAPE_BIBTEX_KEY = False

def normchar(char_descriptor):
    return unicodedata.lookup(char_descriptor).lower()


din5007_variant2_translation = [
    [normchar('LATIN CAPITAL LETTER A WITH DIAERESIS'), 'ae'],  # Auml
    [normchar('LATIN CAPITAL LETTER O WITH DIAERESIS'), 'oe'],  # Ouml
    [normchar('LATIN CAPITAL LETTER U WITH DIAERESIS'), 'ue'],  # Uuml
    [normchar('LATIN SMALL LETTER A WITH DIAERESIS'), 'ae'],  # auml
    [normchar('LATIN SMALL LETTER O WITH DIAERESIS'), 'oe'],  # ouml
    [normchar('LATIN SMALL LETTER U WITH DIAERESIS'), 'ue'],  # uuml
    [normchar('LATIN SMALL LETTER SHARP S'), 'ss'],  # szlig
    [normchar('LATIN SMALL LETTER E WITH GRAVE'), 'e'],  # egrave
    [normchar('LATIN SMALL LETTER E WITH ACUTE'), 'e'],  # eacute
]

d_escape = dict(din5007_variant2_translation)


def escape_bibtexkey(s, default_char="_"):
    import string

    res = ""
    for c in s:
        if c in string.ascii_letters + string.digits + "-_+:":
            res = res + c
            continue
        elif c in d_escape:
            res = res + d_escape[c]
        else:
            res = res + default_char
    return res


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
    import datetime

    now = datetime.datetime.now().isoformat()
    now = now.replace('T', '_').replace(':', '-')
    now = now.split('.')[0]
    return now


def save_import_file(filename):
    import core.config as config

    temppath = config.get("paths.tempdir")
    _filename_only = filename.split(os.path.sep)[-1]
    # leave following in for windows: "/" in path representation possible there
    _filename_only = filename.split("/")[-1]
    destname = os.path.join(temppath, "bibtex_import_saved_" + getNow() + "_" + _filename_only)
    logg.info("bibtex import: going to copy/save import file %s -> %s", filename, destname)
    shutil.copyfile(filename, destname)

    return


article_types = [
    ("article", "An article from a journal or magazine.",
     ("author", "title", "journal", "year"),
     ("volume", "number", "pages", "month", "note", "key")),
    ("misc", "Use this type when nothing else seems appropriate.",
     (),
     ("author", "title", "howpublished", "month", "year", "note", "key")),
    ("unpublished", "A document with an author and title, but not formally published. ",
     ("author", "title", "note"),
     ("month", "year", "key")),
    ("book", "A book with an explicit publisher. ",
     ("author or editor", "title", "publisher", "year"),
     ("volume", "series", "address", "edition", "month", "note", "key")),
    ("booklet", "A work that is printed and bound, but without a named publisher or sponsoring institution.",
     ("title",),
     ("author", "howpublished", "address", "month", "year", "note", "key")),
    ("inbook", "A part of a book, which may be a chapter and/or a range of pages. ",
     ("author or editor", "title", "chapter and/or pages", "publisher", "year"),
     ("volume", "series", "address", "edition", "month", "note", "key")),
    ("manual", "Technical documentation. ",
     ("title"),
     ("author", "organization", "address", "edition", "month", "year", "note", "key")),
    ("techreport", "A report published by a school or other institution, usually numbered within a series. ",
     ("author", "title", "institution", "year"),
     ("type", "number", "address", "month", "note", "key")),
    ("conference",
     "An article in the proceedings of a conference. This entry is identical to the 'inproceedings' entry and is included for compatibility with another text formatting system. ",
     ("author", "title", "booktitle", "year"),
     ("editor", "pages", "organization", "publisher", "address", "month", "note", "key")),
    ("proceedings", " The proceedings of a conference.",
     ("title", "year"),
     ("editor", "publisher", "organization", "address", "month", "note", "key")),
    ("inproceedings", "An article in the proceedings of a conference. ",
     ("author", "title", "booktitle", "year"),
     ("editor", "pages", "organization", "publisher", "address", "month", "note", "key")),
    ("incollection", "A part of a book with its own title.",
     ("author", "title", "booktitle", "year"),
     ("editor", "pages", "organization", "publisher", "address", "month", "note", "key")),
    ("phdthesis", "A PhD thesis.",
     ("author", "title", "school", "year"),
     ("address", "month", "note", "key")),
    ("mastersthesis", "A Master's thesis.",
     ("author", "title", "school", "year"),
     ("address", "month", "note", "key"))]


from . import schema as schema


def getAllBibTeXTypes():
    return [bibname for bibname, description, required, optional in article_types]


def getbibtexmappings():
    bibtextypes = {}
    for metatype in schema.loadTypesFromDB():
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


def checkMappings():
    s = getbibtexmappings()
    for bibname, description, required, optional in article_types:
        if bibname not in s:
            print bibname, "is not associated with any metatype"
        else:
            print bibname, "->", s[bibname]


def detecttype(doctype, fields):
    results = []
    for bibname, description, required, optional in article_types:
        score = 0
        if doctype.lower() == bibname.lower():
            score += 120
        score -= len(required)
        for field in required:
            if field in fields:
                score += 20
        for field in optional:
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
    return record


def importBibTeX(infile, node=None, req=None):
    if req:
        try:
            user = users.getUserFromRequest(req)
            msg = "bibtex import: import started by user '%s'" % (user.name)
        except:
            msg = "bibtex import: starting import (unable to identify user)"
    else:
        msg = "bibtex import: starting import (%s)" % ustr(sys.argv)
    logg.info(msg)

    bibtextypes = getbibtexmappings()
    result = []
    entries = []

    if isinstance(infile, list):
        entries = infile
    else:
        node = node or Directory(utf8_decode_escape(os.path.basename(infile)))
        try:
            save_import_file(infile)
            with codecs.open(infile, "r", encoding="utf-8") as fi:
                parser = BibTexParser()
                parser.customization = _bibteximport_customize
                bibtex = bibtex_load(fi, parser=parser)
        except Exception as e:
            logg.error("bibtex import: bibtexparser failed: {}".format(e))
            raise ValueError("bibtexparser failed")

    logg.info("bibtex import: %d entries", len(entries))

    for count, fields in enumerate(bibtex.entries):
        docid_utf8 = fields["ID"]
        fields["key"] = fields.pop("ID")
        doctype = fields.pop("ENTRYTYPE")
        mytype = detecttype(doctype, fields)

        if mytype:
            fieldnames = {}
            datefields = {}
            if mytype not in bibtextypes:
                logg.error("bibtex mapping of bibtex type '%s' not defined - import stopped", mytype)
                raise MissingMapping(msg)
            result += [(mytype.lower(), fields)]

            metatype = bibtextypes[mytype]

            # check for mask configuration
            metadatatype = q(Metadatatype).filter_by(name=metatype).one()
            mask = metadatatype.get_mask(u"bibtex_import") or metadatatype.get_mask(u"bibtex")
            if mask:
                for f in mask.all_maskitems:
                    try:
                        _bib_name = q(Node).get(f.get(u"mappingfield")).name
                        _mfield = q(Node).get(f.get(u"attribute"))
                        _med_name = _mfield.name
                        if _mfield.get(u"type") == u"date":
                            datefields[_med_name] = _mfield.get(u"valuelist")
                    except AttributeError as e:
                        msg = "bibtex import docid='{}': field error for bibtex mask for type {} and bibtex-type '{}': {}"
                        msg = msg.format(docid_utf8, metatype, mytype, e)
                        logg.error(msg)
                    else:
                        fieldnames[_bib_name] = _med_name

            doc = Document(docid_utf8,schema=metatype)
            for k, v in fields.items():
                if k in fieldnames.keys():
                    k = fieldnames[k]  # map bibtex name

                if k in datefields.keys():  # format date field
                    v = str(parse_date(v, datefields[k]))

                doc.set(k, v)

            child_id = None
            child_type = None
            try:
                node.children.append(doc)
                child_id = doc.id
                child_type = doc.type
            except Exception as e:
                logg.exception("bibtex exception")
                raise ValueError()

    logg.debug("bibtex import: finished import")
    print msg

    return node
