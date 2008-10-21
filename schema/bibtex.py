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

    This code was tested with 963 bibtex entries from 17 different bibtex
    files, and appears to work so far.
"""

import re
import os

token = re.compile(r'@\w+\s*{|[a-zA-Z-]+\s*=\s*{?["\'{]|[a-zA-Z-]+\s*=\s+[0-9a-zA-Z_]')
comment = re.compile(r'%[^\n]*\n')
delim = re.compile(r'\W')
frontgarbage = re.compile(r'^\W*')
backgarbage = re.compile(r'[ \n\t}"\',]*$')
xspace = re.compile(r'\s+')

counterpiece = {"{":"}",'"':'"',"'":"'"}

def getentries(filename):
    fi = open(filename, "rb")
    data = fi.read()
    fi.close()
    data = data.replace("\r", "\n")
    data = comment.sub('\n', data)
    recordnr = 1

    size = len(data)
    pos = 0
    records = []
    fields = {}
    doctype = None
    while 1:
        m = token.search(data,pos)
        if not m:
            break
        start = m.start()
        end = m.end()
        if data[start]=='@':
            # new entry
            doctype = data[start+1:end-1].strip().lower()
            m = delim.search(data,end)
            if m and m.start()>end:
                key = data[end:m.start()].strip()
                pos = m.end()
            else:
                key = "record%05d" % recordnr
                recordnr = recordnr + 1
                pos = m.end()
            fields = {}
            records += [(doctype,key,fields)]
        elif doctype:
            # new record
            s = data[start:end]

            if end and data[end-1].isalnum():
                # for the \w+\s*=\s+[0-9a-zA-Z_] case
                end = end-1
            
            field = s[:s.index("=")].strip().lower()
            pos = end
            next = token.search(data,pos)
            if next:
                content = data[pos:next.start()]
            else:
                content = data[pos:]

            content = content.replace("{","")
            content = content.replace("~"," ")
            content = content.replace("}","")
            content = xspace.sub(" ",backgarbage.sub("",frontgarbage.sub("",content)))
            content = content.replace("\\\"u","ü").replace("\\\"a","ä").replace("\\\"o","ö") \
                             .replace("\\\"U","Ü").replace("\\\"A","Ä").replace("\\\"O","Ö")
            content = content.replace("\\","")
            content = content.replace("{\"u}","ü").replace("{\"a}","ä").replace("{\"o}","ö") \
                             .replace("{\"U}","Ü").replace("{\"A}","Ä").replace("{\"O}","Ö")
            content = content.strip()

            content = unicode(content,"utf-8",errors='replace').encode("utf-8")

            if field=="author" and content:
                authors = []
                for author in content.split(" and "):
                    author = author.strip()
                    if "," not in author and " " in author:
                        i = author.rindex(' ') 
                        if i>0:
                            forename,lastname=author[0:i].strip(),author[i+1:].strip()
                        author = "%s, %s" % (lastname, forename)
                    authors += [author]
                content = ";".join(authors)

            fields[field] = content
        else:
            pos = end
    return records

#article_types = [
#("article", "bibtex-article", "dt-zeitschriftenaufsatz",
# ["author", "title", "journal", "year", "volume", "number", "pages", "month", "note"]),
#("book,booklet,inbook", "bibtex-book", "dt-buch", 
# ["author", "editor", "title", "publisher", "year", "volume", "number", "series", "address", "edition", "month", "note"]),
#("manual,techreport,report", "bibtex-report", "dt-report",
# ["author", "title", "institution", "year", "address", "month", "number", "note"]),
#("proceedings,conference", "bibtex-proceedings", "dt-konferenzband",
# ["title", "year", "editor", "volume", "number", "series", "address", "publisher", "note", "month", "organization"]),
#("inproceedings", "bibtex-inproceedings", "dt-konferenzbeitrag",
# ["author", "title", "booktitle", "year", "editor", "volume", "number", "series", "pages", "address", "month", "organization", "publisher", "note"]),
#("incollection", "bibtex-incollection", "dt-buchbeitrag",
# ["author", "title", "booktitle", "publisher", "year", "editor", "volume", "number", "series", "chapter", "pages", "address", "edition", "month", "note"]),
#("phdthesis", "bibtex-incollection", "diss",
# ["author", "title", "school", "year"]),
#("mastersthesis", "bibtex-incollection", "diss",
# ["author", "title", "school", "year"])
#]

article_types = [
("article", "An article from a journal or magazine.",
 ("author","title","journal","year"),
 ("volume","number","pages","month","note","key")),
("misc", "Use this type when nothing else seems appropriate.",
 (),
 ("author","title","howpublished","month","year","note","key")),
("unpublished", "A document with an author and title, but not formally published. ",
 ("author","title","note"),
 ("month","year","key")),
("book", "A book with an explicit publisher. ",
 ("author or editor","title","publisher","year"),
 ("volume","series","address","edition","month","note","key")),
("booklet", "A work that is printed and bound, but without a named publisher or sponsoring institution.",
 ("title",),
 ("author","howpublished","address","month","year","note","key")),
("inbook", "A part of a book, which may be a chapter and/or a range of pages. ",
 ("author or editor","title","chapter and/or pages","publisher","year"),
 ("volume","series","address","edition","month","note","key")),
("manual", "Technical documentation. ",
 ("title"),
 ("author","organization","address","edition","month","year","note","key")),
("techreport", "A report published by a school or other institution, usually numbered within a series. ",
 ("author","title","institution","year"),
 ("type","number","address","month","note","key")),
("conference", "An article in the proceedings of a conference. This entry is identical to the 'inproceedings' entry and is included for compatibility with another text formatting system. ",
 ("author","title","booktitle","year"),
 ("editor","pages","organization","publisher","address","month","note","key")),
("proceedings", " The proceedings of a conference.",
 ("title","year"),
 ("editor","publisher","organization","address","month","note","key")),
("inproceedings", "An article in the proceedings of a conference. ",
 ("author","title","booktitle","year"),
 ("editor","pages","organization","publisher","address","month","note","key")),
("incollection", "A part of a book with its own title.",
 ("author","title","booktitle","year"),
 ("editor","pages","organization","publisher","address","month","note","key")),
("phdthesis", "A PhD thesis.",
 ("author","title","school","year"),
 ("address","month","note","key")),
("mastersthesis", "A Master's thesis.",
 ("author","title","school","year"),
 ("address","month","note","key"))]

import core
import core.tree as tree
import schema as schema

def getAllBibTeXTypes():
    return [bibname for bibname, description, required, optional in article_types]

def getbibtexmappings():
    bibtextypes = {}
    for metatype in schema.loadTypesFromDB():
        for bibtextype in metatype.get("bibtexmapping").split(";"):
            if bibtextype:
                bibtextypes[bibtextype] = metatype.getName()
    return bibtextypes

def checkMappings():
    s = getbibtexmappings()
    for bibname, description, required, optional in article_types:
        if bibname not in s:
            print bibname,"is not associated with any metatype"
        else:
            print bibname,"->",s[bibname]

def detecttype(doctype, fields):
    results = []
    for bibname, description, required, optional in article_types:
        score = 0
        if doctype.lower()==bibname.lower():
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
    score,bibname = max(results)

    if score>=30:
        return bibname
    else:
        return None

class MissingMapping:
    def __init__(self, message=""):
        self.message = message
    def __str__(self):
        return self.message

def importBibTeX(file, node=None):
    bibtextypes = getbibtexmappings()
    result = []

    if not node:
        node = tree.Node(name=os.path.basename(file), type="directory")

    for doctype, docid, fields in getentries(file):
        mytype = detecttype(doctype, fields)
        if mytype:
            if mytype not in bibtextypes:
                raise MissingMapping("bibtex mapping of bibtex type '%s' not defined" % mytype)
            result += [(mytype.lower(), fields)]

            metatype = bibtextypes[mytype]
            doc = tree.Node(docid, type="document/"+metatype)
            fieldnames = [field.getName() for field in doc.getMetaFields()]
            for k,v in fields.items():
                if k not in fieldnames: 
                    kk = [k]
                    if k=="number":
                        kk = ["number", "issue"]
                    elif k=="author":
                        kk = ["author", "author.fullname_comma", "author.fullname"]
                    elif k=="school":
                        kk = ["school", "origin"]
                    elif k=="year":
                        kk = ["year", "year-accepted"]

                    for k in kk:
                        if (k+"-contrib") in fieldnames:
                            k = k+"-contrib"
                            break
                        elif k+"-title" in fieldnames:
                            k = k+"-title"
                            break
                        elif k.startswith("book") and ("congress"+k[4:]) in fieldnames:
                            k = ("congress"+k[4:]) 
                            break
                        elif ("congress-"+k) in fieldnames:
                            k = ("congress-"+k) 
                            break
                        elif k.startswith("book") and ("journal-"+k[4:]) in fieldnames:
                            k = ("journal-"+k[4:]) 
                            break
                        elif ("journal-"+k) in fieldnames:
                            k = ("journal-"+k) 
                            break
                        elif k.startswith("book") and ("bookseries-"+k[4:]) in fieldnames:
                            k = ("bookseries-"+k[4:]) 
                            break
                        elif ("bookseries-"+k) in fieldnames:
                            k = ("bookseries-"+k) 
                            break
                        elif ("p-"+k) in fieldnames:
                            k = ("p-"+k) 
                            break

                if k not in fieldnames:
                    print mytype,"->",metatype,"!",k
                print k,v
                doc.set(k,v)
            node.addChild(doc)
    return node

def test():
    try:
        b = tree.getRoot("bibs")
        tree.getRoot().removeChild(b)
    except:
        pass

    b = tree.Node("bibs",type="directory")
    tree.getRoot().addChild(b)
    #import glob
    #for file in glob.glob("/home/mis/tmp/bib/*"):
    #    c = tree.Node(os.path.basename(file),type="directory")
    #    b.addChild(c)
    #    importBibTeX(file,c)
    file = "../file.bib"
    c = tree.Node(os.path.basename(file),type="directory")
    b.addChild(c)
    importBibTeX(file,c)


