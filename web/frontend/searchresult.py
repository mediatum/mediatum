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
from utils.utils import getAllCollections, u
from core.styles import theme
from web.frontend import Content
from utils.strings import ensure_unicode_returned
from contenttypes.container import Collections, Collection, Container
from schema.searchmask import SearchMaskItem

q = db.query


logg = logging.getLogger(__name__)


class SearchResult(Content):

    def __init__(self, resultlist, query, collections=[]):
        self.query = query
        self.collections = collections
        self.active = -1
        self.error = 0

        if resultlist is None:
            self.resultlist = []
            self.error = 1
        else:
            self.resultlist = resultlist
            for result in resultlist:
                result.parent = self

    def feedback(self, req):
        if "scoll" in req.params:
            id = req.args.get("scoll", type=int)
            for nr in range(len(self.resultlist)):
                if self.resultlist[nr].collection.id == id:
                    self.active = nr
        elif self.active >= 0:
            return self.resultlist[self.active].feedback(req)

    def in_list(self, id):
        if self.active >= 0:
            c = self.resultlist[self.active]
            if hasattr(c, "in_list") and c.in_list(id):
                return 1
        return 0

    def getLink(self, collection):
        return 'node?scoll=' + collection.id

    def getContentStyles(self):
        return []

    @ensure_unicode_returned(name="searchresult:html")
    def html(self, req):
        if self.error > 0:
            return req.getTAL(theme.getTemplate("searchresult.html"), {
                              "query": self.query, "r": self, "collections": self.collections, "language": lang(req)}, macro="error")

        if self.active < 0:
            if len(self.resultlist) == 0:
                return req.getTAL(theme.getTemplate("searchresult.html"), {
                                  "query": self.query, "r": self, "collections": self.collections, "language": lang(req)}, macro="noresult")
            else:
                if len(self.resultlist) == 1:
                    self.resultlist[self.active].feedback(req)
                    return self.resultlist[self.active].html(req)
                else:
                    return req.getTAL(theme.getTemplate("searchresult.html"),
                                      {"query": self.query,
                                       "collections": self.collections,
                                       "reslist": self.resultlist,
                                       "r": self,
                                       "language": lang(req)},
                                      macro="listcollections")
        else:
            self.resultlist[self.active].feedback(req)
            return self.resultlist[self.active].html(req)


def protect(s):
    return '"' + s.replace('"', '') + '"'

# method handles all parts of the simple search


def simple_search(req):
    from web.frontend.content import ContentList
    searchquery = req.form.get("query")

    # test whether this query is restricted to a number of collections
    collection_ids = []
    for key in req.params:
        if key.startswith("c_"):
            collection_ids.append(key[2:])
            
    # no collection means: all collections
    if collection_ids:
        collection_query = q(Container).filter(Container.id.in_(collection_ids))
    else:
        collection_query = q(Collections).one().container_children
        
    # TODO: access.filter collections
    collections = collection_query.all()
    
    if logg.isEnabledFor(logging.DEBUG):
        logg.debug("simple_search with query '%s' on %s collections: %s", searchquery, len(collections), [c.name for c in collections])
    
    def do_search(start_node): 
        result = start_node.search('full=' + searchquery).all()
#             result = access.filter(result)
        if len(result) > 0:
            cl = ContentList(result, start_node, [])
            cl.feedback(req)
            cl.linkname = "Suchergebnis"
            cl.linktarget = ""
            return cl
            
    act_node_id = req.form.get("act_node", type=int)
    act_node = q(Node).get(act_node_id) if act_node_id else None
    if act_node is not None and not isinstance(act_node, Collections):
        # actual node is a collection or directory
        single_result = do_search(act_node)
        res = [single_result] if single_result else []
    else:
        # actual node is collections-node
        res = [cl for cl in (do_search(collection) for collection in collections) if cl is not None]
        
    if logg.isEnabledFor(logging.DEBUG):
        logg.debug("%s result sets found with %s nodes", len(res), len([n for cl in res for n in cl.files]))

    if len(res) == 1:
        return res[0]
    else:
        return SearchResult(res, searchquery, collections)


def _extended_searchquery_from_req(req):
    max_fields = 3
    if req.form.get("searchmode") == "extendedsuper":
        max_fields = 10

    q_str = u''
    q_user = u''
    first2 = 1
    for i in range(1, max_fields + 1):
        query_key = "query" + unicode(i)
        # for range queries
        query_to_key = "query" + unicode(i) + "-to"
        query_from_key = "query" + unicode(i) + "-from"
        field_id_or_name = req.form.get("field" + unicode(i), "").strip()
        element_query = req.form.get(query_key, "").strip()

        if not element_query and query_from_key not in req.form:
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
                if query_to_key in req.form and field.getFieldtype() == "date":
                    date_from = "0000-00-00T00:00:00"
                    date_to = "0000-00-00T00:00:00"
                    
                    from_value = req.form.get(query_from_key)
                    if from_value:
                        date_from = date.format_date(date.parse_date(from_value, field.getValues()), "%Y-%m-%dT%H:%M:%S")
                            
                    to_value = req.form.get(query_to_key)
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
                    q_str += field.name + "=" + protect(element_query)
                    
                    if field.label:
                        q_user += field.label + " = " + protect(element_query)
                    else:
                        q_user += field.name + " = " + protect(element_query)

            q_str += ")"
    
    return q_str, q_user.strip()


def extended_search(req):
    from web.frontend.content import ContentList
        
    collection_id = req.form.get("collection", type=int)
    if collection_id:
        collection = q(Collection).get(collection_id)
    else:
        # no collection id given -> search starts at collection root
        collection = q(Collections).one()

    searchquery, readable_query = _extended_searchquery_from_req(req)

    logg.debug("extended_search with query '%s' on collection '%s'(%s)", searchquery, collection.name, collection.id)
        
    act_node_id = req.form.get("act_node", type=int)
    act_node = q(Node).get(act_node_id) if act_node_id else None
    
    search_collection = act_node if act_node is not None else collection
    
    result = search_collection.search(searchquery).all()
    
#         result = access.filter(result)
#         logg.info(access.user.name + "%s xsearch for '%s', %s results", access.user.name, q_user, len(result))

    if len(result) > 0:
        cl = ContentList(result, collection, readable_query)
        cl.feedback(req)
        cl.linkname = ""
        cl.linktarget = ""
        return cl
    
    return SearchResult([], readable_query)