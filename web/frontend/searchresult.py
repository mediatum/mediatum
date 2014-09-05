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
import sys
import utils.date as date
import logging
from core.acl import AccessData
from core.translation import lang, translate
from utils.utils import intersection,getAllCollections, u
from core.styles import theme

class SearchResult:
    def __init__(self, resultlist, query, collections=[]):
        self.query = query
        self.collections = collections
        self.active = -1
        self.error = 0
        
        if resultlist==None:
            self.resultlist = []
            self.error = 1
        else:
            self.resultlist = resultlist
            for result in resultlist:
                result.parent = self
            
    def feedback(self,req):
        if "scoll" in req.params:
            id = req.params["scoll"]
            for nr in range(len(self.resultlist)):
                if self.resultlist[nr].collection.id == id:
                    self.active = nr
        elif self.active>=0:
            return self.resultlist[self.active].feedback(req)

    def in_list(self,id):
        if self.active>=0:
            c = self.resultlist[self.active]
            if hasattr(c, "in_list") and c.in_list(id):
                return 1
        return 0

    def getLink(self,collection):
        return 'node?scoll='+collection.id
        
    def getContentStyles(self):
        return []

    def html(self,req):
        if self.error>0:
            return req.getTAL(theme.getTemplate("searchresult.html"), {"query":self.query, "r":self, "collections":self.collections, "language":lang(req)}, macro="error")
            
        if self.active<0:
            if len(self.resultlist)==0:
                return req.getTAL(theme.getTemplate("searchresult.html"), {"query":self.query, "r":self, "collections":self.collections, "language":lang(req)}, macro="noresult")
            else:
                if len(self.resultlist)==1:
                    self.resultlist[self.active].feedback(req)
                    return self.resultlist[self.active].html(req)
                else:
                    return req.getTAL(theme.getTemplate("searchresult.html"), {"query":self.query,"collections":self.collections,"reslist":self.resultlist,"r":self, "language":lang(req)}, macro="listcollections")
        else:
            self.resultlist[self.active].feedback(req)
            return self.resultlist[self.active].html(req)

def protect(s):
    return '"'+s.replace('"','')+'"'
   
# method handles all parts of the simple search
def simple_search(req):
    from web.frontend.content import ContentList
    res = []
    words = []
    collections = []
    collection_ids = {}
    
    access = AccessData(req)
    q = u(req.params.get("query", ""))

    # test whether this query is restricted to a number of collections
    for key,value in req.params.items():
        if key.startswith("c_"):
            collection_ids[key[2:]] = 1
    # no collection means: all collections
    if len(collection_ids) == 0 or 1 in collection_ids.keys():
        for collection in access.filter(tree.getRoot("collections").getChildren()):
            collection_ids[collection.id] = 1

    # now retrieve all results in all collections
    for collection in getAllCollections():
        if collection.id in collection_ids:
            collections.append(collection)

    num = 0
    logging.getLogger('usertracing').info(access.user.name + " search for '"+q+"', "+str(num)+" results")
    try:
        if  req.params.get("act_node",None) and tree.getNode(req.params.get("act_node")).getContentType()!="collections":
            # actual node is a collection or directory
            result = tree.getNode(req.params.get("act_node")).search('full='+q)
            result = access.filter(result)
            num += len(result)
            if len(result)>0:
                cl = ContentList(result, collection, words)
                cl.feedback(req)
                cl.linkname = "Suchergebnis"
                cl.linktarget = ""
                res.append(cl)
        else:
            # actual node is collections-node
            for collection in collections:
                result = collection.search('full='+q)
                result = access.filter(result)
                num += len(result)

                if len(result)>0:
                    cl = ContentList(result, collection, words)
                    cl.feedback(req)
                    cl.linkname = "Suchergebnis"
                    cl.linktarget = ""
                    res.append(cl)

        if len(res)==1:
            return res[0]
        else:
            return SearchResult(res, q, collections)
    except:
        return SearchResult(None, q, collections)

# method handles all parts of the extended search
def extended_search(req):
    from web.frontend.content import ContentList
    max = 3
    if req.params.get("searchmode")=="extendedsuper":
        max = 10
    sfields=[]
    access = AccessData(req)
    metatype = None
    
    collectionid = req.params.get("collection",tree.getRoot().id)
    try:
        collection = tree.getNode(collectionid)
    except:
        for coll in tree.getRoot("collections").getChildren():
            collection = tree.getNode(coll.id)
            break

    q_str = ''
    q_user = ''
    first2 = 1
    for i in range(1,max+1):       
        f = u(req.params.get("field"+str(i),"").strip())
        q = u(req.params.get("query"+str(i),"").strip())

        if not q and "query"+str(i)+"-from" not in req.params:
            continue
        
        if not first2:
            q_str += " and "
            q_user += " %s " %(translate("search_and", request=req))
            
        first2 = 0

        if not f.isdigit():
            q = u(req.params.get("query"+str(i),"").strip())
            q_str += f + '=' + protect(q)
            q_user += f + '=' + protect(q)
        else:
            masknode = tree.getNode(f)
            assert masknode.type == "searchmaskitem"
            first = 1
            q_str += "("
            for metatype in masknode.getChildren():
                if not first:
                    q_str += " or "
                    q_user += " %s " %(translate("search_or", request=req))
                first = 0
                if "query"+str(i)+"-from" in req.params and metatype.getFieldtype()=="date":
                    date_from = "0000-00-00T00:00:00"
                    date_to = "0000-00-00T00:00:00"
                    fld = metatype
                    if str(req.params["query"+str(i)+"-from"])!="":
                        date_from = date.format_date(date.parse_date(str(req.params["query"+str(i)+"-from"]), fld.getValues()), "%Y-%m-%dT%H:%M:%S")
                    if str(req.params["query"+str(i)+"-to"])!="":
                        date_to = date.format_date(date.parse_date(str(req.params["query"+str(i)+"-to"]), fld.getValues()), "%Y-%m-%dT%H:%M:%S")

                    if date_from=="0000-00-00T00:00:00" and date_to!=date_from: # from value
                        q_str += metatype.getName()+ ' <= '+date_to
                        q_user += "%s &le; \"%s\"" %(metatype.getName(), str(req.params["query"+str(i)+"-to"]))
                        
                    elif date_to=="0000-00-00T00:00:00" and date_to!=date_from: # to value
                        q_str += metatype.getName()+ ' >= '+date_from
                        q_user += "%s &ge; \"%s\"" %(metatype.getName(), str(req.params["query"+str(i)+"-from"]))
                    else:
                        #q_str += '('+metatype.getName()+' >= '+date_from+' and '+metatype.getName()+' <= '+date_to+')'
                        q_str += '('+metatype.getName()+' = '+date_from+')'
                        
                        q_user += "(%s %s \"%s\" %s \"%s\")" %(metatype.getName(), translate("search_between", request=req), str(req.params["query"+str(i)+"-from"]), translate("search_and", request=req), str(req.params["query"+str(i)+"-to"]))
                else:
                    q = u(req.params.get("query"+str(i),"").strip())
                    q_str += metatype.getName() + '=' + protect(q)
                    if metatype.getLabel()!="":
                        q_user += "%s = %s" %(metatype.getLabel(), protect(q))
                    else:
                        q_user += "%s = %s" %(metatype.getName(), protect(q))

            q_str += ")"
    try:
        if req.params.get("act_node","") and req.params.get("act_node")!=str(collection.id):
            result = tree.getNode(req.params.get("act_node")).search(q_str)
        else:
            result = collection.search(q_str)
        result = access.filter(result)
        logging.getLogger('usertracing').info(access.user.name + " xsearch for '"+q_user+"', "+str(len(result))+" results")
        if len(result)>0:
            cl = ContentList(result, collection, q_user.strip())
            cl.feedback(req)
            cl.linkname = ""
            cl.linktarget = ""
            return cl
        return SearchResult([],q_user.strip())
    except:
        return SearchResult(None,q_user.strip())

