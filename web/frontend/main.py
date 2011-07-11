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
import core.tree as tree
import os
import re

import core.acl 
import core.config as config
from utils.utils import *
from core.acl import AccessData
from web.frontend.frame import getNavigationFrame
from web.frontend.content import getContentArea, ContentNode
import core.xmlnode as xmlnode

def display(req):
    req.session["area"] = ""
    content = getContentArea(req)
    content.feedback(req)
    try: # add export mask data of current node to request object
        mask = getMetaType(content.actNode().getSchema()).getMask('head_meta')
        req.params['head_meta'] = mask.getViewHTML([content.actNode()], flags=8)
    except:
        req.params['head_meta'] = ''
    
    navframe = getNavigationFrame(req)
    navframe.feedback(req)

    contentHTML = content.html(req)
    navframe.write(req, contentHTML)

def display_noframe(req):
    content = getContentArea(req)
    content.feedback(req)
    
    navframe = getNavigationFrame(req)
    navframe.feedback(req)
    req.params["show_navbar"] = 0

    contentHTML = content.html(req)
    
    if "raw" in req.params:
        req.write(contentHTML)
    else:
        navframe.write(req, contentHTML, show_navbar=0)

# needed for workflows:

PUBPATH = re.compile("/?(publish|pub)/(.*)$")
def publish(req):
    m = PUBPATH.match(req.path)

    node = tree.getRoot("workflows")
    if m: 
        for a in m.group(2).split("/"):
            if a: 
                try:
                    node = node.getChild(a)
                except tree.NoSuchNodeError:
                    return 404
    
    req.params["id"] = node.id

    content = getContentArea(req)
    content.content = ContentNode(node)
    req.session["area"] = "publish"
    
    return display_noframe(req)

def show_parent_node(req):
    id = req.params.get("id")
    node = tree.getNode(id)
    parent = None
    for p in node.getParents():
        if p.type != "directory" and p.type != "collection":
            parent = p
    
    req.params["id"] = parent.id
    req.params["obj"] = node.id

    content = getContentArea(req)
    content.content = ContentNode(parent)

    return display_noframe(req)

def esc(v):
    return v.replace("\\","\\\\").replace("'","\\'")

def exportsearch(req, xml=0):  # format 0=pre-formated, 1=xml, 2=plain
    access = AccessData(req)
    access = core.acl.getRootAccess()
    
    id = req.params.get("id")
    q = req.params.get("q","")
    lang = req.params.get("language", "")
    collections = tree.getRoot("collections")

    if xml:
        req.reply_headers['Content-Type'] = "text/xml; charset=utf-8"
        req.write('<?xml version="1.0" encoding="utf-8"?>')

    else:
        req.reply_headers['Content-Type'] = "text/plain; charset=utf-8"

    try:
        node = tree.getNode(id)
    except tree.NoSuchNodeError:
        if xml:
            req.write("<error>Invalid ID</error>")
        else:
            req.write("var error='invalid id';")
        return
    if not isParentOf(node,collections):
        if xml:
            req.write("<error>Invalid ID</error>")
        else:
            req.write("var error='invalid id';")
        return

    if not q:
        nodes = access.filter(node.search("objtype=document"));
    else:
        #nodes = access.filter(node.search("objtype=document and "+q));
        nodes = access.filter(node.search(q));

    limit = int(req.params.get("limit", 99999))
    sortfield = req.params.get("sort", None)
    
    if sortfield:
        nodes = nodes.sort(sortfield)

    if limit < len(nodes):
        nodes = nodes[0:limit]

    if xml: # xml
        req.write("<nodelist>")
        i = 0
        for node in nodes:
            s = xmlnode.getSingleNodeXML(node)
            req.write(s)
            i = i+1
        req.write("</nodelist>")

    elif req.params.get("data", None):
        req.write('a=new Array(%d);' % len(nodes))
        i = 0
        for node in nodes:
            req.write('a[%d] = new Object();\n' % i);
            req.write("  a[%d]['nodename'] = '%s';\n" % (i,node.name))
            for k,v in node.items():
                req.write("    a[%d]['%s'] = '%s';\n" % (i,esc(k),esc(v)))
            i = i + 1
        req.write('add_data(a);\n')
    else:
        req.write('a=new Array(%d);' % len(nodes))
        i = 0
        labels = int(req.params.get("labels",1))
        for node in nodes:
            req.write('a[%d] = new Object();\n' % i);
            req.write("a[%d]['text'] = '%s';\n" % (i,esc(node.show_node_text(labels=labels, language=lang))));
            req.write("a[%d]['link'] = 'http://%s?id=%s';\n" % (i, config.get('host.name'),node.id));
            i = i + 1
        req.write('add_data(a);\n')
    print "%d node entries xml=%d" % (i, xml)
       
def xmlsearch(req):
    return exportsearch(req, xml=1)

def jssearch(req):
    return exportsearch(req, xml=0)
