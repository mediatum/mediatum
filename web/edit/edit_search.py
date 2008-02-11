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
import core.athana as athana
import core.acl as acl
import core.tree as tree
import logging
import utils.date as date
from core.acl import AccessData
import string
from edit_common import EditorNodeList, shownodelist
from schema.schema import getMetaType

log = logging.getLogger('edit')
utrace = logging.getLogger('usertracing')

def protect(s):
    return '"'+s.replace('"','')+'"'

def search_results(req,id):
    access = AccessData(req)

    if "Reset" in req.params:
        return search_form(req, id, "edit_search_reset_msg")
    
    try:
        searchvalues = req.session["esearchvals"]
    except:
        req.session["esearchvals"] = searchvalues = {}

    node = tree.getNode(id)
    objtype = req.params["objtype"]
    type = getMetaType(objtype)
    
    query = ""

    if "full" in req.params:
        value = req.params["full"]
        searchvalues[objtype + ".full"] = value
        for word in value.split(" "):
            if word:
                if query:
                    query += " and "
                query += "full=" + protect(word)
 
    for field in type.getMetaFields():
        if field.Searchfield():
            name=field.getName()
            if name in req.params:
                value = req.params[name].strip()
                if value:
                    searchvalues[objtype + "." + field.getName()] = value
                    if field.getFieldtype()=="list" or field.getFieldtype()=="ilist" or field.getFieldtype()=="mlist":
                        if query:
                            query += " and "
                        query += name + "=" + protect(value)
                    else:
                        for word in value.split(" "):
                            if word:
                                if query:
                                    query += " and "
                                query += name + "=" + protect(word)

    utrace.info(access.user.name + " search for "+query)

    nodes = node.search(query)
    
    req.session["nodelist"] = EditorNodeList(nodes)

    if len(nodes):
        req.writeTAL("web/edit/edit_search.html", {"id":id}, macro="start_new_search")
        shownodelist(req, nodes)
    else:
        search_form(req, id, "edit_search_noresult_msg")

def search_form(req, id, message=None):
    node = tree.getNode(id)
    occur = node.getAllOccurences(AccessData(req))

    objtype = req.params.get("objtype", None)
    if objtype:
        req.session["lastobjtype"] = objtype
    else:
        try: objtype = req.session["lastobjtype"]
        except: pass

    if message:
        req.writeTAL("web/edit/edit_search.html", {"message":message}, macro="write_message")

    if "Reset" in req.params:
        try: del req.session["esearchvals"]
        except: pass

    try:
        searchvalues = req.session["esearchvals"]
    except:
        req.session["esearchvals"] = searchvalues = {}

    
    f = []
    otype = None
    mtypelist = []
    itemlist = {}
    for mtype,num in occur.items():
        print mtype.getContentType(),mtype.getSchema()
        if num>0 and mtype.getDescription():
            if otype is None:
                otype = mtype
            if mtype.getSchema() not in itemlist:
                itemlist[mtype.getSchema()] = None
                mtypelist.append(mtype)

                if objtype == mtype.getSchema():
                    otype = mtype
            else:
                log.warning("Warning: Unknown metadatatype: "+mtype.getName())

    formlist = []
    if otype:
        for field in otype.getMetaFields():
            if field.Searchfield() and field.getFieldtype()!="date":
                value = searchvalues.get(otype.getSchema()+"."+field.getName(),"")
                formlist.append([field, value])
                if field.getFieldtype()=="list" or field.getFieldtype()=="mlist":
                    f.append(field.getName())

    script = '<script>\n l = Array("'+string.join(f, '", "')+'");'
    script+="""
            for (var i = 0; i < l.length; ++i) {
                obj = document.getElementById(l[i]);
                if (obj){
                    obj.selectedIndex=-1;
                }
            }
        </script>"""

    try:
        indexdate = date.format_date(date.parse_date(tree.getRoot().get("lastindexerrun")), "%Y-%m-%d %H:%M:%S")
    except:
        indexdate = None

    req.writeTAL("web/edit/edit_search.html",{"node":node, "occur":occur, "mtypelist":mtypelist, "objtype":objtype, "searchvalues":searchvalues.get(str(otype)+".full", ""), "script":script, "indexdate":indexdate, "formlist":formlist},macro="search_form")

    return


def edit_search(req, ids):

    if "search" in req.params and req.params["search"] == "run":
        search_results(req,ids[0])
    else:
        search_form(req,ids[0])


