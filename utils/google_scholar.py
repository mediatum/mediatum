"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

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
from datetime import datetime
from utils import esc
from core.systemtypes import Metadatatypes
from core import Node, db
import core.config as config
import logging
import time
from core.athana import http_request
from core.request_handler import make_param_dict_utf8_values

q = db.query

logg = logging.getLogger(__name__)

"""
    simple cache dictionary for the head_meta mask for each schema
    every schema (key) has a dictionary as value with the following keys:
        "mappings": dictionary of mappingfields (key) and attributes (value) of mask head_meta if fieldtype is 'mapping'
        "attributes": list of mappingfields if fieldtype is 'attribute'
        "creation_time": creation time in seconds, if creation time is older than 24 hours, the cacheentry for this
                         schema is renewed
"""
head_meta_cache = {}

def convert_date(date_str):
    """
    scan date_str with several date formats and convert it in a format for google_scholar: yyyy, yyyy/mm or yyyy/mm/dd
    :param date_str: date as string
    :return: yyyy (if month missing), yyyy/mm (if day missing) otherwise yyyy/mm/dd
    """
    flag_no_month = 1
    flag_no_day = 2
    time_pattern = [ ("%Y-%m-%dT%H:%M:%S", 0),
                     ("%Y-%m-00T%H:%M:%S", flag_no_day),
                     ("%Y-00-00T%H:%M:%S", flag_no_month),
                     ("%Y-%m-%d %H:%M:%S", 0),
                     ("%Y-%m-00 %H:%M:%S", flag_no_day),
                     ("%Y-%m-%d", 0),
                     ("%Y-%m", flag_no_day),
                     ("%Y", flag_no_month),
                     ("%d.%m.%Y", 0),
                     ]
    exceptions = []

    scan_ok = False
    for (pattern, flag) in time_pattern:
        try:
            tm = datetime.strptime(date_str, pattern)
        except ValueError as e:
            exceptions.append(e.message)
        else:
            scan_ok = True
            break

    if not scan_ok:
        return ''
    try:
        if flag == flag_no_month:
            return tm.strftime("%Y")
        if flag == flag_no_day:
            return tm.strftime("%Y/%m")
        return tm.strftime("%Y/%m/%d")
    except ValueError as e:
        logg.exception('convert_date: cannot convert %s: %s', date_str, e.message)
        return ''

def get_author_list(line):
    """
    create a list of single authors from a line with authors which are separated by a ';' or by a ','
    :param line: line with authors
    :return: list with single authors, or empty list if no authors found
    """
    authors = []
    line = line.strip()
    while line.endswith(',') or line.endswith(';'):
        line = line[:-1]

    # authors may be also split with ' und ', ' and ' or ' AND '
    line = line.replace(' und ', ';').replace(' and ', ';').replace(' AND ', ';')
    if line.count(';') > 0:
        # authors separated by ';'
        authors = line.split(';')
    elif line.count(',') > 1:
        # two cases possible:
        # author1-firstname author1-lastname, author2-firstname, author2-lastname   or
        # author1-lastname, author1-firstname-initials, author2-lastname, author2-firstname-initials
        authors = line.split(',')
        # if every twice entry has an '.' then this is the second case
        # second case has also an even number of authors
        initials_possible = len(authors) % 2 == 0
        if initials_possible:
            idx = 0
            for author in authors:
                if idx % 2 == 0 and author.find('.') >= 0:
                    initials_possible = False
                    break
                if idx % 2 == 1 and author.find('.') < 0:
                    initials_possible = False
                    break
                idx += 1

        if initials_possible:
            new_authors = []
            for idx in range(0, len(authors) / 2):
                new_authors.append(authors[2 *idx] + ',' + authors[2 * idx + 1])
            authors = new_authors

    elif line.count(',') == 1:
        # two cases possible:
        # author1, author2  or
        # author-lastname, author-firstname
        author_lastname = line.split(',')[0].strip()
        if len(author_lastname.split(' ')) > 1:
            # author_lastname contains more than one word, so this may be two authors separated by ','
            authors =  line.split(',')
        else:
            # one author, lastname is separated from firstname by a ','
            authors = [line]
    else:
        # single author
        authors = [line]

    authors = [a.strip() for a in authors if a.strip()]
    return authors

dummy_request = http_request(*([None] * 6))
dummy_request.args = make_param_dict_utf8_values([])


def chk_citation_pdf_url(mappingfield):
    """
    check existence of citation_pdf_url, uses therefore the function _send_file_with_type from core.athana with the
    new parameter checkonly=True.
    The function_send_file_with_type needs a parameter of the class http_request, but only path and args (which can be
    the empty list) are needed, so a dummy_request object is used where the path is set accordingly
    :param mappingfield: metafield for citation_pdf_url like
            u'<meta name="citation_pdf_url" content="http://mediatum.ub.tum.de/doc/602482/file.pdf"/>' 
    :return:True if citation_pdf_url exists else False
    """

    from web.frontend.filehandlers import _send_file_with_type
    if mappingfield.find("http://") >= 0:
        path = mappingfield.split("http://")[1]
    elif mappingfield.find("https://") >= 0:
        path = mappingfield.split("https://")[1]
    else:
        return False
    path = path[path.find('/'):]
    dummy_request.path = path
    status =_send_file_with_type("document", None, dummy_request, checkonly=True)
    return status == 200


def google_scholar(node):
    """
    create meta tags for google_scholar, use exportmask head_meta to get the definitions for the meta tags
    at least citation_title, citation_author and citation_publication_date must be provided otherwise an
    empty string is returned
    :param node: 
    :return: string with meta tags
    """
    result = u''
    title_flag = False
    author_flag = False
    publication_date_flag = False

    head_meta_entry = {}
    mappings = {}
    attributes = []

    if not config.get("websearch.google_scholar", "").lower() == "true" or not node or node.isContainer():
        return ""

    use_cache = config.get("websearch.google_scholar_cache", "").lower() == "true"

    if use_cache and node.schema in head_meta_cache.keys():
        head_meta_entry = head_meta_cache[node.schema]
        if time.time() - head_meta_entry['last_timestamp'] > (24 * 60 * 60): # expired after 24 hours
            head_meta_cache.pop(node.schema)

    if not use_cache or node.schema not in head_meta_cache.keys():
        if use_cache:
            head_meta_entry = {"last_timestamp": time.time(), "mappings" : {}, "attributes": []}
            head_meta_cache[node.schema] = head_meta_entry
        mtype = q(Metadatatypes).one().children.filter_by(name=node.schema).scalar()
        if not mtype:
            return ""
        mask = mtype.getMask('head_meta')
        if not mask:
            return ""
        for item in mask.children:
            fieldtype = item.get('fieldtype')
            if fieldtype == 'mapping':
                try:
                    mappingfield = int(item.get('mappingfield'))
                    attribute = int(item.get('attribute'))
                    mapping = q(Node).get(mappingfield)
                    if not mapping:
                        continue
                    metafield = q(Node).get(attribute)
                    if not metafield:
                        continue
                    if mapping.name in mappings.keys():
                        mappings[mapping.name].append(metafield.name)
                    else:
                        mappings[mapping.name] = [metafield.name]
                except ValueError as e:
                    continue
            elif fieldtype == 'attribute':
                attributes.append(item.get('mappingfield'))
                continue
            else:
                continue

        if use_cache:
            head_meta_entry['mappings'] = mappings
            head_meta_entry['attributes'] = attributes
            head_meta_cache[node.schema] = head_meta_entry

    if use_cache:
        head_meta_entry = head_meta_cache[node.schema]
        if not head_meta_entry and not head_meta_entry["mappings"] and not head_meta_entry["attributes"]:
            return ""

        mappings = head_meta_entry['mappings']
        attributes = head_meta_entry['attributes']

    for mapping_name in mappings.keys():

        for metafield_name in mappings[mapping_name]:
            mfield = node.get(metafield_name)
            if mfield == '':
                continue
            if mapping_name == u'citation_author':
                authors = get_author_list(mfield)
                if authors:
                    author_flag = True

                for author in authors:
                    result += u'<meta name="citation_author" content="%s">\n' % esc(author)
            else:
                if mapping_name == u'citation_publication_date':
                    mfield = convert_date(mfield)
                    if mfield:
                        publication_date_flag = True

                if mapping_name == u'citation_title' or mapping_name == u"citation_conference_title":
                    title_flag = True
                result += u'<meta name="%s" content="%s">\n' % (mapping_name, esc(mfield))

    for item in attributes:
        mappingfield = item.replace('[att:id]', str(node.id))
        # meta tag must not have a '/>' only '>' is allowed
        if mappingfield.endswith('/>'):
            mappingfield = mappingfield[:-2] + '>'
        if mappingfield.find('citation_pdf_url') >= 0:
            if not chk_citation_pdf_url(mappingfield):
                continue
        result += mappingfield + '\n'


    if title_flag and author_flag and publication_date_flag:
        return result
    return ""
