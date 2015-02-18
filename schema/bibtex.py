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
import sys
import codecs
import logging
import unicodedata

import core.users as users
from .schema import getMetaType
from utils.utils import u, u2, utf8_decode_escape
from utils.date import parse_date


logg = logging.getLogger(__name__)

ESCAPE_BIBTEX_KEY = False
VERBOSE = True


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
    if os.sep == '/':
        ret = os.system("cp %s %s" % (filename, destname))
    else:
        cmd = "copy %s %s" % (filename, destname)
        ret = os.system(cmd.replace('/', '\\'))

    if ret & 0xff00:
        raise IOError("Couldn't copy %s to %s (error: %s)" % (filename, destname, ustr(ret)))

    return


def getentries(filename):
    save_import_file(filename)

    fi = codecs.open(filename, "r", encoding="utf-8")

    try:
        data = fi.read()
    except UnicodeDecodeError:
        fi.close()
        logg.error("bibtex import: getentries(filename): encoding error when trying codec 'utf-8', filename was %s", filename)
        logg.info("bibtex import: getentries(filename): going to try without codec 'utf-8', filename was %s", filename)

        try:
            fi = codecs.open(filename, "r")
            try:
                data = fi.read()
                data = u2(data)
            except Exception:
                fi.close()
                logg.exception("bibtex import: getentries(filename): error at second attempt", exc_info=1)

                raise MissingMapping("wrong encoding")
        except Exception:
            logg.exception("bibtex import: getentries(filename): error at second attempt")

            raise MissingMapping("wrong encoding")
    try:
        fi.close()
    except:
        pass

    data = data.replace("\r", "\n")
    # throw out BOM
    try:
        data = u2(data).replace('\xef\xbb\xbf', "")
    except:
        pass
    data = comment.sub('\n', data)
    recordnr = 1

    size = len(data)
    pos = 0
    records = []
    fields = {}
    doctype = None
    placeholder = {}
    while True:
        m = token.search(data, pos)
        if not m:
            break
        start = m.start()
        end = m.end()
        if data[start] == '@':
            doctype = data[start + 1:end - 1].replace("{", "").strip().lower()
            m = delim2.search(data[end:])
            if m:  # and m.start()>end:
                key = data[end:end + m.end()].strip()
                pos = end + m.end()
                if key[-1] == ",":
                    key = key[0:-1]
            else:
                key = "record%05d" % recordnr
                recordnr = recordnr + 1
                #pos = m.end()
                pos = end

            if ESCAPE_BIBTEX_KEY:
                key = escape_bibtexkey(key)

            fields = {}
            key = u2(key)
            fields["key"] = key
            records += [(doctype, key, fields)]

            if doctype == "string":
                # found placeholder
                t2 = re.compile(r'[^}]*')
                x = t2.search(data, end)
                x_start = x.start()
                x_end = x.end()
                s = data[x_start:x_end + 1]
                key, value = s.split("=")

                placeholder[key.strip()] = value.strip()[1:-1]
                pos = x_end

                if VERBOSE:
                    try:
                        logg.debug("bibtex import: placeholder: key='%s', value='%s'", key.strip(), value.strip()[1:-1])
                    except Exception:
                        try:
                            logg.exception("bibtex import: placeholder: key='%s', value='%s'",
                                key.strip(), value.strip()[1:-1].encode("utf8", "replace"))
                        except Exception:
                            logg.exception("bibtex import: placeholder: 'not printable key-value pair'")

        elif doctype:
            # new record
            s = data[start:end]

            if end and data[end - 1].isalnum():
                # for the \w+\s*=\s+[0-9a-zA-Z_] case
                end = end - 1

            field = s[:s.index("=")].strip().lower()
            pos = end
            next_token = token.search(data, pos)
            if next_token:
                content = data[pos:next_token.start()]
            else:
                content = data[pos:]

            content = content.replace("{", "")
            content = content.replace("~", " ")
            content = content.replace("}", "")

            for key in placeholder:
                content = content.replace(key, placeholder[key])

            # some people use html entities in their bibtex...
            content = content.replace("&quot;", "'")
            content = xspace.sub(" ", backgarbage.sub("", frontgarbage.sub("", content)))

            content = u(content)
            content = content.replace("\\\"u", "\xc3\xbc").replace("\\\"a", "\xc3\xa4").replace("\\\"o", "\xc3\xb6") \
                .replace("\\\"U", "\xc3\x9c").replace("\\\"A", "\xc3\x84").replace("\\\"O", "\xc3\x96")
            content = content.replace("\\\'a", "\xc3\xa0").replace("\\\'A", "\xc3\x80").replace("\\vc", "\xc4\x8d") \
                .replace("\\vC", "\xc4\x8c")
            content = content.replace("\\", "")
            content = content.replace("{\"u}", "\xc3\xbc").replace("{\"a}", "\xc3\xa4").replace("{\"o}", "\xc3\xb6") \
                .replace("{\"U}", "\xc3\x9c").replace("{\"A}", "\xc3\x84").replace("{\"O}", "\xc3\x96")

            content = content.strip()

            if field in ["author", "editor"] and content:
                authors = []
                for author in content.split(" and "):
                    author = author.strip()
                    if "," not in author and " " in author:
                        i = author.rindex(' ')
                        if i > 0:
                            forename, lastname = author[0:i].strip(), author[i + 1:].strip()
                        author = "%s, %s" % (lastname, forename)
                    authors += [author]
                content = ";".join(authors)

            fields[field] = content
        else:
            pos = end
    return records


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

import core.tree as tree
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
    shortcut = {}

    if isinstance(infile, list):
        entries = infile
    else:
        if not node:
            node = tree.Node(name=utf8_decode_escape(os.path.basename(infile)),
                             type="directory")
        try:
            entries = getentries(infile)
        except:
            msg = "bibtex import: getentries failed, import stopped (encoding error)"
            logg.error(msg)
            raise ValueError("getentries failed")

    logg.info("bibtex import: %d entries", len(entries))

    counter = 0
    for doctype, docid, fields in entries:
        counter += 1
        docid_utf8 = utf8_decode_escape(docid)

        mytype = detecttype(doctype, fields)

        if doctype == "string":
            if VERBOSE:
                logg.debug("bibtex import:       processing %s: %s, %s --> (is string)", counter, doctype, docid)
            continue

        if mytype:
            fieldnames = {}
            datefields = {}

            if mytype == "string":
                continue

            elif mytype not in bibtextypes:
                logg.error("bibtex mapping of bibtex type '%s' not defined - import stopped", mytype)
                raise MissingMapping(msg)
            result += [(mytype.lower(), fields)]

            metatype = bibtextypes[mytype]

            # check for mask configuration
            mask = getMetaType(metatype).getMask("bibtex_import")
            if not mask:
                mask = getMetaType(metatype).getMask("bibtex")
            if mask:
                for f in mask.getMaskFields():
                    try:
                        _bib_name = tree.getNode(f.get("mappingfield")).getName()
                        _mfield = tree.getNode(f.get("attribute"))
                        _med_name = _mfield.getName()

                        if _mfield.get("type") == "date":
                            datefields[_med_name] = _mfield.get("valuelist")

                    except tree.NoSuchNodeError as e:
                        msg = "bibtex import docid='%s': field error for bibtex mask for type %s and bibtex-type '%s': %s: " % (
                            docid_utf8, metatype, mytype, e)
                        msg = msg + "_bib_name='%s', _mfield='%s', _med_name='%s'" % (
                            ustr(_bib_name), ustr(_mfield), ustr(_med_name))
                        logg.error(msg)
                        continue

                    fieldnames[_bib_name] = _med_name

            doc = tree.Node(docid_utf8, type="document/" + metatype)
            for k, v in fields.items():
                if k in fieldnames.keys():
                    k = fieldnames[k]  # map bibtex name

                if k in datefields.keys():  # format date field
                    v = parse_date(v, datefields[k])

                doc.set(k,  utf8_decode_escape(v))

            child_id = None
            child_type = None
            try:
                node.addChild(doc)
                doc.setDirty()
                child_id = doc.id
                child_type = doc.type
            except Exception as e:
                logg.exception("bibtex exception")
                raise ValueError()

            if VERBOSE:
                try:
                    logg.info("bibtex import: done  processing %s: %s, %s --> type=%s, id=%s",
                        counter, doctype, docid, child_type, child_id)
                except Exception:
                    try:
                        logg.info("bibtex import: done  processing %s: %s, %s --> type=%s, id=%s",
                            counter, doctype, docid.decode("utf8", "replace"), child_type, child_id)
                    except Exception:
                        logg.info("bibtex import: done  processing %s: %s, %s --> type=%s, id=%s",
                            ustr(counter), doctype, "'not printable bibtex key'", child_type, child_id)
    logg.debug("bibtex import: finished import")
    print msg

    return node


def test():
    try:
        b = tree.getRoot("bibs")
        tree.getRoot().removeChild(b)
    except:
        pass

    b = tree.Node("bibs", type="directory")
    tree.getRoot().addChild(b)
    #import glob
    # for file in glob.glob("/home/mis/tmp/bib/*"):
    #    c = tree.Node(os.path.basename(file),type="directory")
    #    b.addChild(c)
    #    importBibTeX(file,c)
    file = "../file.bib"
    c = tree.Node(os.path.basename(file), type="directory")
    b.addChild(c)
    importBibTeX(file, c)
