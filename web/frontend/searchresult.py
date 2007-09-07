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
import core.tree as tree
import core.athana as athana
import sys
import utils.date as date
import logging
from core.acl import AccessData
from core.translation import lang


class SearchResult:
    def __init__(self,resultlist,query,collections=[]):
        self.resultlist = resultlist
        self.query = query
        self.collections = collections

    def feedback(self,req):
        if "dir" in req.params:
            id = req.params["dir"]
            for item in self.resultlist:
                if item.collection.id == id:
                    return item # switch to collection node

    def getLink(self,collection):
        return 'node?dir='+collection.id

    def html(self,req):
        if len(self.resultlist) == 0:
            return req.getTAL("web/frontend/searchresult.html", {"query":self.query, "r":self, "collections":self.collections, "language":lang(req)}, macro="noresult")
        else: #len(self.resultlist) > 1:
            return req.getTAL("web/frontend/searchresult.html", {"query":self.query,"collections":self.collections,"reslist":self.resultlist,"r":self, "language":lang(req)}, macro="listcollections")

def protect(s):
    return '"'+s.replace('"','')+'"'

# method handles all parts of the simple search
def simple_search(req):
    access = AccessData(req)
    q = req.params.get("query","")
    
    # test whether this query is restricted to a number of collections
    collection_ids = {}
    for key,value in req.params.items():
        if key.startswith("c_"):
            collection_ids[key[2:]] = 1
    # no collection means: all collections
    if len(collection_ids) == 0 or 1 in collection_ids.keys():
        for collection in access.filter(tree.getRoot("collections").getChildren()):
            collection_ids[collection.id] = 1

    print collection_ids
    logging.getLogger('usertracing').info(access.user.name + " search for '"+q+"'")
    # now retrieve all results in all collections
    resultlist = []
    collections = []
    for collection in tree.getRoot("collections").getChildren():
        if collection.id in collection_ids:
            collections.append(collection)
            result = collection.search(protect(q))
            words = result.getDescription().split(" ")
            if words == ['']:
                words = []
            result = access.filter(result)
            if len(result):
                ids = []
                for node in result:
                    ids.append(node.id)
                from frontend.content import ContentList
                c = ContentList(tree.NodeList(ids),collection,words)
                c.linkname = "Suchergebnis"
                c.linktarget = ""
                resultlist += [c]
 
    if len(resultlist) == 1:
        return resultlist[0]
    else:
        return SearchResult(resultlist,q, collections)

# method handles all parts of the extended search
def extended_search(req):
    access = AccessData(req)
    
    collectionid = req.params.get("collection",tree.getRoot().id)
    try:
        collection = tree.getNode(collectionid)
    except:
        for coll in tree.getRoot("collections").getChildren():
            collection = tree.getNode(coll.id)
            break

    occurs = collection.getAllOccurences()
    sfields=[]

    # get all searchfields
    for mtype, num in occurs.items():
        if num>0:
            for f in mtype.getSearchFields():
                sfields.append(f)

    query = ""
    querytext = ""

    metatype = None
    for i in range(1,3+1):       
        f=req.params.get("field"+str(i),"").strip()
        for sfield in sfields:
            if sfield.getName() == f:
                metatype = sfield

        if "query"+str(i)+"-from" in req.params and metatype and metatype.getFieldtype()=="date":
            # date field
            fld=metatype

            date_from = 0
            date_to = 2097151
            if str(req.params["query"+str(i)+"-from"])!="":
                date_from = date.parse_date(str(req.params["query"+str(i)+"-from"]), fld.getValues()).daynum()
            if str(req.params["query"+str(i)+"-to"])!="":
                date_to = date.parse_date(str(req.params["query"+str(i)+"-to"]), fld.getValues()).daynum()

            if query:
                query+=" and "
            query += "%s=%d-%d" % (f,date_from, date_to)
        
        elif metatype and metatype.getFieldtype() in ["list","mlist","ilist"]:
            q = req.params["query"+str(i)].strip()
            if q:
                if query:
                    query+=" and "
                query += "%s=%s" % (f,protect(q))
                querytext += q + " "
        else:
            # normal field
            try:
                q = req.params["query"+str(i)].strip()
                if q !="":
                    for word in q.split(" "):
                        if word:
                            if query:
                                query+=" and "
                            query += "%s=%s" % (f,protect(word))
                    querytext += q + " "
            except:
                q = ""
    try:
        type = req.params["type"]
        if query:
            query += " and "
        query += "objtype=%s" % type
    except KeyError:
        pass

    logging.getLogger('usertracing').info(access.user.name + " xsearch for '"+query+"'")

    result = collection.search(query)
    words = result.getDescription().split(' ')
    if words == ['']:
        words = []
    result = access.filter(result)
    if len(result):
        ids = []
        for node in result:
            ids.append(node.id)
        from frontend.content import ContentList
        c = ContentList(tree.NodeList(ids),collection,querytext.strip())
        c.linkname = "Suchergebnis"
        c.linktarget = ""
        return c
    else:
        return SearchResult([],querytext.strip())


