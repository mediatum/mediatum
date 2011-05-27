"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Arne Seifert <seiferta@in.tum.de>

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

import os
import core.tree as tree
import core.acl as acl
import core.users as users
import core.config as config

from core.translation import translate, lang, t
from utils.fileutils import importFileIntoDir, getImportDir
from core.news import newstypes, NewsItem, getNewsFile, getNewsItems, deleteNewsEntry, modifyNewsEntry
from lib.FCKeditor import fckeditor
from web.edit.edit_common import upload_for_html
from utils.date import format_date, parse_date

d_format = 'dd.mm.yyyy'
d_formatlong = 'dd.mm.yyyy HH:MM:SS'

def getInformation():
    return {"version":"1.0", "system":0}


def deliverEditForm(req, newsid=""):
    global newstypes
    node = tree.getNode(req.params.get("id"))
    
    operation = "add"
    nitem = NewsItem("\t".join(["","","","","","","0","memo",""]))
    if newsid!="":
        for item in getNewsItems(getNewsFile(node)):
            if item.getId()==newsid:
                nitem = item
                operation = "edit"
                break
    
    v = {
        'newstypes': newstypes,
        'item': nitem,
        'operation': operation,
        'd_format': d_format,
        'd_formatlong': d_formatlong,
        'node': node,
        'language': lang(req)
    }

    try:
        os.environ['HTTP_USER_AGENT'] = req.request.request_headers['HTTP_USER_AGENT']
    except:
        os.environ['HTTP_USER_AGENT'] = req.request.request_headers['user-agent']

    return req.getTAL("web/edit/modules/news.html", v, macro="news_modify")


def deliverContent(req, node):
    nf = getNewsFile(node)

    if not nf: # create files
        nf = open(config.get("paths.tempdir")+"/"+node.id+".new", "w")
        nf.write("# newsfile for node %s\n" %(node.id))
        nf.close()
    
        nf = importFileIntoDir(getImportDir()+"/"+node.id+".new", config.get("paths.tempdir")+node.id+".new")
        node.addFile(nf)

    return req.getTAL("web/edit/modules/news.html", {"items":getNewsItems(nf), "d_format":d_format, "d_formatlong":d_formatlong}, macro="news_content")


def getContent(req, ids):
    user = users.getUserFromRequest(req)
    if "news" in users.getHideMenusForUser(user):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")
    
    ids = ids[0] # use only first selected node
    node = tree.getNode(ids)
    error = ""
    
    v = {}
    v['error'] = error
    v['node'] = node
    v['tab'] = req.params.get("tab", "")
    v['ids'] = ids
    v['content'] = deliverContent(req, node)
    
    if node.getType() not in ["collections", "collection"]:
        error = "wrong_nodetype"
        
    if req.params.get("option", "")=="htmlupload":
        # use fileupload
        req.write(upload_for_html(req))
        return ""
        
    for key in req.params:
        if key.startswith("add_item"):
            v['content'] = deliverEditForm(req)
            break
        
        if key.startswith("save"):
            visible = "0"
            if "news_visible" in req.params.keys():
                visible = "1"
            _news_text = req.params.get("news_text", "").replace("\r", "").replace("\n", "").replace("\t", "")
            
            try:
                _news_datefrom = format_date(parse_date(req.params.get("news_datefrom", ""), d_format),"%Y-%m-%d")
            except:
                _news_dateform = ""
            try:
                _news_dateuntil = format_date(parse_date(req.params.get("news_dateuntil", ""), d_format),"%Y-%m-%d")
            except:
                _news_dateuntil = ""
            try:    
                _news_date = format_date(parse_date(req.params.get("news_date", ""), d_format),"%Y-%m-%d")
            except:
                _news_date = ""
            news_item = NewsItem("\t".join([req.params.get("news_id", ""), _news_datefrom, _news_dateuntil, _news_date, format_date(), req.params.get("news_title", ""), visible, req.params.get("news_type", ""), _news_text]))
            modifyNewsEntry(node, news_item)    
   
            v['content'] = deliverContent(req, node)
            break
        
        if key.startswith("delete_"):
            deleteNewsEntry(node, key[7:-2])
            v['content'] = deliverContent(req, node)
            break
    
        if key.startswith("edit_"):
            v['content'] = deliverEditForm(req, newsid=key[5:-2])
            break

    return req.getTAL("web/edit/modules/news.html", v, macro="edit_news")

