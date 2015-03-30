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
import json
import logging

import core.acl
import core.config as config
import core.users as users
import core.xmlnode as xmlnode
from utils.utils import *
from core.acl import AccessData
from core.metatype import Context
from core.translation import lang
from web.frontend.frame import getNavigationFrame
from web.frontend.content import getContentArea, ContentNode
from schema.schema import getMetadataType, getMetaType
from core.transition import httpstatus
from contenttypes.data import Content


logg = logging.getLogger(__name__)


def handle_json_request(req):
    s = []
    if req.params.get("cmd") == "get_list_smi":
        searchmaskitem_id = req.params.get("searchmaskitem_id")
        f = None
        g = None
        if searchmaskitem_id and searchmaskitem_id != "full":
            f = tree.getNode(searchmaskitem_id).getFirstField()
        if not f:  # All Metadata
            f = g = getMetadataType("text")
        s = [f.getSearchHTML(Context(g, value=req.params.get("query_field_value"), width=174, name="query" + ustr(req.params.get("fieldno")),
                                     language=lang(req), collection=tree.getNode(req.params.get("collection_id")),
                                     user=users.getUserFromRequest(req), ip=req.ip))]
    req.write(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
    return


DISPLAY_PATH = re.compile("/([-.~_/a-zA-Z0-9]+)$")
known_node_aliases = {}


def display_404(req):
    return httpstatus.HTTP_NOT_FOUND


def display_alias(req):
    match = DISPLAY_PATH.match(req.path)
    if match:
        alias = match.group(1).rstrip("/").lower()
        node_id = known_node_aliases.get(alias)
        if node_id is not None:
            logg.debug("known node alias in cache '%s' -> '%s'", alias, node_id)
            req.params["id"] = node_id
        else:
            node_id = db.get_aliased_nid(alias)
            if node_id:
                known_node_aliases[alias] = node_id
                req.params["id"] = node_id
                logg.debug("node alias from DB '%s' -> '%s'", alias, node_id)
            else:
                logg.info("node alias not found: '%s'", alias)
                # pass illegal id => nice error msg is displayed
                req.params["id"] = "-1"
        # node is set now, redirect to regular display handler
        display(req)
    else:
        raise Exception(u"illegal alias '{}', should not be passed to this handler!".format(alias))


def display(req):
    if "jsonrequest" in req.params:
        handle_json_request(req)
        return

    req.session["area"] = ""
    content = getContentArea(req)
    content.feedback(req)
    try:  # add export mask data of current node to request object
        act_node = content.actNode()
        if act_node and isinstance(act_node, Content):
            mdt = getMetaType(act_node.schema)
        else:
            mdt = None
        mask = mdt.getMask('head_meta') if mdt is not None else None
        req.params['head_meta'] = mask.getViewHTML([content.actNode()], flags=8) if mask is not None else u''
    except:
        # XXX: the "common exception cases" here were act_node, mdt, mask == None. This is handled in the try-block now. 
        # Other exceptions should indicate a real failure.
        logg.exception("exception in display, setting head_meta to empty string")
        req.params['head_meta'] = ''
    navframe = getNavigationFrame(req)
    navframe.feedback(req)

    contentHTML = content.html(req)
    contentHTML = modify_tex(contentHTML, 'html')
    navframe.write(req, contentHTML)
    # set status code here... 
    req.setStatus(content.status())
    # ... Don't return a code because Athana overwrites the content if an http error code is returned from a handler.


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
    parent = None
    try:
        node = tree.getNode(req.params.get("id"))
    except tree.NoSuchNodeError:
        return display_noframe(req)

    for p in node.getParents():
        if p.type != "directory" and p.type != "collection":
            parent = p
    if not parent:
        return display_noframe(req)

    req.params["id"] = parent.id
    req.params["obj"] = node.id

    content = getContentArea(req)
    content.content = ContentNode(parent)

    return display_noframe(req)


def esc(v):
    return v.replace("\\", "\\\\").replace("'", "\\'")


def exportsearch(req, xml=0):  # format 0=pre-formated, 1=xml, 2=plain
    access = AccessData(req)
    access = core.acl.getRootAccess()

    id = req.params.get("id")
    q = req.params.get("q", "")
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
    if not isParentOf(node, collections):
        if xml:
            req.write("<error>Invalid ID</error>")
        else:
            req.write("var error='invalid id';")
        return

    if not q:
        nodes = access.filter(node.search("objtype=document"))
    else:
        #nodes = access.filter(node.search("objtype=document and "+q));
        nodes = access.filter(node.search(q))

    limit = int(req.params.get("limit", 99999))
    sortfield = req.params.get("sort", None)

    if sortfield:
        nodes = nodes.sort_by_fields(sortfield)

    if limit < len(nodes):
        nodes = nodes[0:limit]

    if xml:  # xml
        req.write("<nodelist>")
        i = 0
        for node in nodes:
            s = xmlnode.getSingleNodeXML(node)
            req.write(s)
            i = i + 1
        req.write("</nodelist>")

    elif req.params.get("data", None):
        req.write('a=new Array(%d);' % len(nodes))
        i = 0
        for node in nodes:
            req.write('a[%d] = new Object();\n' % i)
            req.write("  a[%d]['nodename'] = '%s';\n" % (i, node.name))
            for k, v in node.attrs.items():
                req.write("    a[%d]['%s'] = '%s';\n" % (i, esc(k), esc(v)))
            i = i + 1
        req.write('add_data(a);\n')
    else:
        req.write('a=new Array(%d);' % len(nodes))
        i = 0
        labels = int(req.params.get("labels", 1))
        for node in nodes:
            req.write('a[%d] = new Object();\n' % i)
            req.write("a[%d]['text'] = '%s';\n" % (i, esc(node.show_node_text(labels=labels, language=lang))))
            req.write("a[%d]['link'] = 'http://%s?id=%s';\n" % (i, config.get('host.name'), node.id))
            i = i + 1
        req.write('add_data(a);\n')
    logg.info("%d node entries xml=%d", i, xml)


def xmlsearch(req):
    return exportsearch(req, xml=1)


def jssearch(req):
    return exportsearch(req, xml=0)
