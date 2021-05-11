# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import itertools as _itertools

import utils.date as date
import logging

import core.translation as _core_translation
from core import Node, db
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
    """This content class is used if no search results can be displayed.
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
        language = _core_translation.set_language(req.accept_languages)
        context = {"language": language,
                   "query": self.query,
                   "container": self.container.getLabel(language),
                   "container_url": node_url(self.container.id)
                  }

        theme = webconfig.theme
        if self.error:
            html = theme.render_template("search_error.j2.jade", context)
        else:
            html = theme.render_template("search_noresult.j2.jade", context)
        return html


def protect(s):
    return '"' + s.replace('"', '') + '"'


def search(searchtype, searchquery, readable_query, paths, req, container_id = None):
    from web.frontend.content import ContentList
    if not container_id:
        container_id = req.args.get("id", type=int)
    container = q(Container).get(container_id) if container_id else None

    # if the current node is not a Container or not accessible by the user, use the collections root instead
    if container is None or not container.has_read_access():
        # XXX: The collections root is always searchable. Could there be situations in which we don't want to allow this?
        # XXX: We could check the read permission for Collections to decide if search is allowed.
        container = get_collections_node()

    def filter_dbquery_results(dbquery):
        return dbquery.filter_read_access()

    try:
        result = container.search(searchquery, filter_dbquery=filter_dbquery_results)
    except SearchQueryException as e:
        # query parsing went wrong or the search backend complained about something
        return NoSearchResult(readable_query, container, readable_query, error=True)

    content_list = ContentList(result, container, paths, words=readable_query)
    try:
        content_list.feedback(req)
    except Exception as e:
        # that should not happen, but is somewhat likely (db failures, illegal search queries that slipped through...),
        # just show 0 result view and don't confuse the user with unhelpful error messages ;)
        logg.exception("exception executing %(searchtype)s search for query %(readable_query)s",
                       dict(searchtype=searchtype, readable_query=readable_query, error=True))
        db.session.rollback()
        return NoSearchResult(readable_query, container, searchtype, error=True)

    language = _core_translation.set_language(req.accept_languages)
    content_list.linkname = u"{}: {} \"{}\"".format(
            container.getLabel(language),
            _core_translation.translate("search_for", language=language),
            readable_query,
        )
    content_list.linktarget = ""

    if content_list.has_elements:
        logg.info("%s search with query '%s' on container %s produced results", searchtype, readable_query, container_id)
        return content_list
    else:
        logg.info("%s search with query '%s' on container %s produced no results", searchtype, readable_query, container_id)
        return NoSearchResult(readable_query, container, searchtype)


def simple_search(req, paths, container_id=None):
    searchquery = req.args.get("query")
    readable_searchquery = searchquery
    if searchquery is None:
        raise ValueError("searchquery param missing!")
    return search("simple", FullMatch(searchquery), readable_searchquery, paths, req, container_id)


def _extended_searchquery_from_req(req):
    for i in range(1, 11 if req.args.get("searchmode") == "extendedsuper" else 4):
        # for range queries
        query_to_key = u"query{}-to".format(unicode(i))
        query_from_key = u"query{}-from".format(unicode(i))
        field_id_or_name = req.args.get(u"field{}".format(unicode(i)), "").strip()
        element_query = req.args.get(u"query{}".format(unicode(i)), "").strip()

        if not element_query and query_from_key not in req.args:
            continue  # no query found, do nothing

        if not field_id_or_name.isdigit():
            yield (
                    u"{} = {}".format(field_id_or_name, protect(element_query)),
                    u"{} = {}".format(field_id_or_name, protect(element_query)),
                   )
            continue

        q_str = list()
        q_user = list()
        for field in q(SearchMaskItem).get(field_id_or_name).children:
            field_type = field.getFieldtype()
            if not (query_to_key in req.args and field_type == "date"):
                if field_type == "number":
                    # exact match
                    q_str.append(u"{} eq {}".format(field.name, protect(element_query)))
                else:
                    # fulltext match
                    q_str.append(u"{} = {}".format(field.name, protect(element_query)))

                if field.label:
                    q_user.append(u"{} = {}".format(field.label, protect(element_query)))
                else:
                    q_user.append(u"{} = {}".format(field.name, protect(element_query)))
                continue

            date_from = "0000-00-00T00:00:00"
            date_to = "0000-00-00T00:00:00"

            from_value = req.args.get(query_from_key)
            if from_value:
                try:
                    date_from = date.format_date(
                            date.parse_date(from_value, field.metatype_data['format']),
                            "%Y-%m-%dT%H:%M:%S",
                           )
                except ValueError:
                    date_from = "9999-00-00T00:00:00"

            to_value = req.args.get(query_to_key)
            if to_value:
                try:
                    date_to = date.format_date(
                            date.parse_date(to_value, field.metatype_data['format']),
                            "%Y-%m-%dT%H:%M:%S",
                           )
                except ValueError:
                    date_from = "0000-00-00T00:00:00"

            if date_from == "0000-00-00T00:00:00" and date_to != date_from:
                q_str.append(u"{} <= {}".format(field.name, date_to))
                q_user.append(u'{} &le; "{}"'.format(field.name, to_value))

            elif date_to == "0000-00-00T00:00:00" and date_to != date_from:
                q_str.append(u"{} >= {}".format(field.name, date_from))
                q_user.append(u'{} &ge; "{}"'.format(field.name, from_value))
            else:
                q_str.append(u'({} >= {} and {} <= {})'.format(field.name, date_from, field.name, date_to))
                q_user.append(u'({} {} "{}" {} "{}")'.format(
                        field.name,
                        _core_translation.translate("search_between", request=req),
                        from_value,
                        _core_translation.translate("search_and", request=req),
                        to_value,
                       ))

        yield (
                u"({})".format(" or ".join(q_str)),
                u" {} ".format(_core_translation.translate("search_or", request=req)).join(q_user),
               )


def extended_search(req, paths):
    searchquery, readable_query = _itertools.izip(*_extended_searchquery_from_req(req))
    searchquery =  " and ".join(searchquery)
    readable_query = " {} ".format(_core_translation.translate("search_and", request=req)).join(readable_query)
    return search("extended", searchquery, readable_query, paths, req)
