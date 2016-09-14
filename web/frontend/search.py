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
from core.search import SearchQueryException
from core import webconfig
from utils.strings import ensure_unicode_returned
from contenttypes.container import Container
from schema.searchmask import SearchMaskItem
from core.webconfig import node_url
from core.search.representation import FullMatch
from core.nodecache import get_collections_node
from web.frontend.contentbase import ContentBase

q = db.query


logg = logging.getLogger(__name__)


class NoSearchResult(ContentBase):
    """This content class is used if no search results cannot be displayed.
    Either the result was empty, or an error happened.
    In the error case, NoSearchResult.error is set to True.
    """

    def __init__(self, query, container, searchmode, error=False):
        self.query = query
        self.container = container
        self.searchmode = searchmode
        self.error = error

    @property
    def node(self):
        return self.container

    @ensure_unicode_returned(name="searchresult:html")
    def html(self, req):
        if self.error:
            return req.getTAL(webconfig.theme.getTemplate("searchresult.html"), {
                              "query": self.query, "r": self, "container": self.container, "language": lang(req)}, macro="error")

        return req.getTAL(webconfig.theme.getTemplate("searchresult.html"), {
                          "query": self.query, "r": self, "container": self.container, "language": lang(req)}, macro="noresult")


def protect(s):
    return '"' + s.replace('"', '') + '"'


def search(searchtype, searchquery, readable_query, paths, req):
    from web.frontend.content import ContentList
    container_id = req.args.get("id", type=int)
    container = q(Container).get(container_id) if container_id else None

    # if the current node is not a Container or not accessible by the user, use the collections root instead
    if container is None or not container.has_read_access():
        # XXX: The collections root is always searchable. Could there be situations in which we don't want to allow this?
        # XXX: We could check the read permission for Collections to decide if search is allowed.
        container = get_collections_node()

    try:
        result = container.search(searchquery).filter_read_access()
    except SearchQueryException as e:
        # query parsing went wrong or the search backend complained about something
        return NoSearchResult(readable_query, container, readable_query, error=True)

    content_list = ContentList(result, container, paths, words=readable_query, show_sidebar=False)
    try:
        content_list.feedback(req)
    except Exception as e:
        # that should not happen, but it somewhat likely (db failures, illegal search queries that slipped through...),
        # just show 0 result view and don't confuse the user with unhelpful error messages ;)
        logg.exception("exception executing %(searchtype)s search for query %(readable_query)s",
                       dict(searchtype=searchtype, readable_query=readable_query, error=True))
        db.session.rollback()
        return NoSearchResult(readable_query, container, searchtype, error=True)

    language = lang(req)
    content_list.linkname = u"{}: {} \"{}\"".format(container.getLabel(language),
                                                    translate("search_for", language=language),
                                                    readable_query)
    content_list.linktarget = ""

    if content_list.has_elements:
        logg.info("%s search with query '%s' on container %s produced results", searchtype, readable_query, container_id)
        return content_list
    else:
        logg.info("%s search with query '%s' on container %s produced no results", searchtype, readable_query, container_id)
        return NoSearchResult(readable_query, container, searchtype)


def simple_search(req, paths):
    searchquery = req.args.get("query")
    readable_searchquery = searchquery
    if searchquery is None:
        raise ValueError("searchquery param missing!")
    return search("simple", FullMatch(searchquery), readable_searchquery, paths, req)


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
                    # XXX: what about dates?
                    if field_type == "number":
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


def extended_search(req, paths):
    searchquery, readable_query = _extended_searchquery_from_req(req)
    return search("extended", searchquery, readable_query, paths, req)
