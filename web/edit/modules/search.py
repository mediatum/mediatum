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

import logging
import utils.date as date
import string
from web.edit.edit_common import EditorNodeList, shownodelist
from schema.schema import getMetaType
from core.metatype import Context
from core.translation import lang
from core.transition import current_user
from core import Node
from core import db
from core.systemtypes import Root
from sqlalchemy import func
from schema.schema import Metadatatype

q = db.query
logg = logging.getLogger(__name__)


def protect(s):
    return '"'+s.replace('"','').replace('\'','')+'"'

def search_results(req,id):
    user = current_user
    if "search" in user.hidden_edit_functions:
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return ""

    if "Reset" in req.params:
        return search_form(req, id, "edit_search_reset_msg")
    
    try:
        searchvalues = req.session["esearchvals"]
    except:
        req.session["esearchvals"] = searchvalues = {}

    node = q(Node).get(id)
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
            if name in req.params and req.params.get(name,"").replace("'",'').replace('"','').strip()!="":
                value = req.params[name].strip()
                
                if value:
                    searchvalues[objtype + "." + field.getName()] = value
                    if field.getFieldtype()=="list" or field.getFieldtype()=="ilist" or field.getFieldtype()=="mlist":
                        if query:
                            query += " and "
                        query += name + "=" + protect(value)
                    else:
                        query += name + "=" + protect(value)

    query += ' and schema="'+req.params.get("objtype","*")+'"'
                                
    logg.info("%s search for %s", user.login_name, query)
    nodes = node.search(query)
    req.session["nodelist"] = EditorNodeList(nodes)

    if len(nodes):
        return req.getTAL("web/edit/modules/search.html", {"id":id}, macro="start_new_search") + shownodelist(req, nodes) 

    return search_form(req, id, "edit_search_noresult_msg")

def search_form(req, id, message=None):
    node = q(Node).get(id)
    ret = ''
    occur = []

    schema_count = node.all_children_by_query(q(Node.schema, func.count(Node.schema)).group_by(Node.schema).order_by(func.count(Node.schema).desc())).all()
    for index, schema_num in enumerate(schema_count):
        schema = q(Metadatatype).filter_by(name=schema_num[0]).first()
        if schema:
            new_tuple = (schema, schema_num[1])
            occur.append(new_tuple)

    objtype = req.params.get("objtype", None)
    if objtype:
        req.session["lastobjtype"] = objtype
    else:
        try: objtype = req.session["lastobjtype"]
        except: pass

    if message:
        ret += req.getTAL("web/edit/modules/search.html", {"message":message}, macro="write_message")

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
    for mtype_count_pair in occur:
        mtype, num = mtype_count_pair[0], mtype_count_pair[1]
        if num > 0 and mtype.getDescription():
            if otype is None:
                otype = mtype
            if mtype.name not in itemlist and mtype.type.find("directory") == -1:
                itemlist[mtype.name] = None
                mtypelist.append(mtype)
                if objtype == mtype.name:
                    otype = mtype
            else:
                logg.warn("Warning: Unknown metadatatype: %s", mtype.getName())

    formlist = []
    if otype:
        for field in otype.metafields:
            if 's' in field.get('opts') and field.getFieldtype() != "date":
                value = searchvalues.get(otype.schema+"."+field.getName(),"")
              
                c = Context(field, value, width=640, name=field.getName(), collection=node, language=lang(req), user=current_user)
                field.searchitem = field.getSearchHTML(c)
                
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
        indexdate = date.format_date(date.parse_date(q(Root).one().get("lastindexerrun")), "%Y-%m-%d %H:%M:%S")
    except:
        indexdate = None
    ctx = {
           "nodes": [node],
           "node": node,
           "occur": occur,
           "mtypelist": mtypelist,
           "objtype": objtype,
           "searchvalues": searchvalues.get(ustr(otype)+".full", ""),
           "script": script,
           "indexdate": indexdate,
           "formlist": formlist
          }

    ret += req.getTAL("web/edit/modules/search.html", ctx, macro="search_form")
    return ret


def getContent(req, ids):

    if "search" in req.params and req.params["search"] == "run":
        return search_results(req,ids[0])
    else:
        return search_form(req,ids[0])


