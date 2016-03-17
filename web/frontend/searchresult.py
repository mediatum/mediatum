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
import utils.date as date
import logging
from core import Node, db
from core.translation import lang, translate
from core.styles import theme
from web.frontend import Content
from utils.strings import ensure_unicode_returned
from contenttypes.container import Collections, Collection, Container
from schema.searchmask import SearchMaskItem
import urllib
from core.webconfig import node_url

q = db.query


logg = logging.getLogger(__name__)


class SearchResult(Content):

    def __init__(self, resultlist, query, container):
        self.query = query
        self.container = container
        self.active = -1
        self.error = 0
        self.searchmode = None

        if resultlist is None:
            self.resultlist = []
            self.error = 1
        else:
            self.resultlist = resultlist
            for result in resultlist:
                result.parent = self

    def feedback(self, req):
        self.searchmode = req.args.get("searchmode")

    def in_list(self, id):
        if self.active >= 0:
            c = self.resultlist[self.active]
            if hasattr(c, "in_list") and c.in_list(id):
                return 1
        return 0

    def getLink(self, container):
        return node_url(container)

    def getContentStyles(self):
        return []

    @ensure_unicode_returned(name="searchresult:html")
    def html(self, req):
        if self.error > 0:
            return req.getTAL(theme.getTemplate("searchresult.html"), {
                              "query": self.query, "r": self, "container": self.container, "language": lang(req)}, macro="error")

        if not self.resultlist:
            return req.getTAL(theme.getTemplate("searchresult.html"), {
                              "query": self.query, "r": self, "container": self.container, "language": lang(req)}, macro="noresult")


def protect(s):
    return '"' + s.replace('"', '') + '"'


def search(searchtype, searchquery, readable_query, req):
    from web.frontend.content import ContentList
    container_id = req.args.get("id", type=int)
    container = q(Container).get(container_id) if container_id else None

    # if the current node is not a Container or not accessible by the user, use the collections root instead
    if container is None or not container.has_read_access():
        container = q(Collections).one()

    result = container.search(searchquery).filter_read_access()
#     result = container.content_children_for_all_subcontainers_with_duplicates

    content_list = ContentList(result, container, readable_query)
    content_list.feedback(req)
    language = lang(req)
    content_list.linkname = u"{}: {} \"{}\"".format(container.getLabel(language),
                                                    translate("search_for", language=language),
                                                    readable_query)
    content_list.linktarget = ""

    if content_list.has_elements:
        logg.info("%s search with query '%s' on container %s produced results", searchtype, searchquery, container_id)
        return content_list
    else:
        logg.info("%s search with query '%s' on container %s produced no results", searchtype, searchquery, container_id)
        return SearchResult([], readable_query, container)


def simple_search(req):
    searchquery = req.args.get("query")
    if searchquery is None:
        raise ValueError("searchquery param missing!")
    return search("simple", u"full=" + searchquery, searchquery, req)


def _extended_searchquery_from_req(req):
    max_fields = 3
    if req.args.get("searchmode") == "extendedsuper":
        max_fields = 10

    q_str = u''
    q_user = u''
    first2 = 1
    for i in range(1, max_fields + 1):
        query_key = "query" + unicode(i)
        # for range queries
        query_to_key = "query" + unicode(i) + "-to"
        query_from_key = "query" + unicode(i) + "-from"
        field_id_or_name = req.args.get("field" + unicode(i), "").strip()
        element_query = req.args.get(query_key, "").strip()

        if not element_query and query_from_key not in req.args:
            # no query found, do nothing
            continue

        if not first2:
            q_str += " and "
            q_user += translate("search_and", request=req) + " "

        first2 = 0

        if not field_id_or_name.isdigit():
            q_str += field_id_or_name + '=' + protect(element_query)
            q_user += field_id_or_name + '=' + protect(element_query)
        else:
            searchmaskitem = q(SearchMaskItem).get(field_id_or_name)
            first = 1
            q_str += "("
            for field in searchmaskitem.children:
                if not first:
                    q_str += " or "
                    q_user += " %s " % (translate("search_or", request=req))
                first = 0
                field_type = field.getFieldtype()
                if query_to_key in req.args and field_type == "date":
                    date_from = "0000-00-00T00:00:00"
                    date_to = "0000-00-00T00:00:00"

                    from_value = req.args.get(query_from_key)
                    if from_value:
                        date_from = date.format_date(date.parse_date(from_value, field.getValues()), "%Y-%m-%dT%H:%M:%S")

                    to_value = req.args.get(query_to_key)
                    if to_value:
                        date_to = date.format_date(date.parse_date(to_value, field.getValues()), "%Y-%m-%dT%H:%M:%S")

                    if date_from == "0000-00-00T00:00:00" and date_to != date_from:
                        q_str += field.name + ' <= ' + date_to
                        q_user += "%s &le; \"%s\"" % (field.name, to_value)

                    elif date_to == "0000-00-00T00:00:00" and date_to != date_from:
                        q_str += field.name + ' >= ' + date_from
                        q_user += "%s &ge; \"%s\"" % (field.name, from_value)
                    else:
                        q_str += u'({} >= {} and {} <= {})'.format(field.name, date_from, field.name, date_to)

                        q_user += "(%s %s \"%s\" %s \"%s\")" % (field.name,
                                                                translate("search_between", request=req),
                                                                from_value,
                                                                translate("search_and", request=req),
                                                                to_value)
                else:
                    if field_type in ("list", "dlist", "hlist", "ilist", "number"):
                        # exact match
                        q_str += field.name + " eq " + protect(element_query)
                    else:
                        # fulltext match
                        q_str += field.name + " = " + protect(element_query)

                    if field.label:
                        q_user += field.label + " = " + protect(element_query)
                    else:
                        q_user += field.name + " = " + protect(element_query)

            q_str += ")"

    return q_str, q_user.strip()

def extended_search(req):
    searchquery, readable_query = _extended_searchquery_from_req(req)
    return search("extended", searchquery, readable_query, req)
