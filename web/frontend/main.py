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
from core.metatype import Context
from core.translation import lang
from web.frontend.frame import getNavigationFrame
from web.frontend.content import getContentArea, ContentNode
from schema.schema import getMetadataType, getMetaType
from core.transition import httpstatus
from contenttypes.data import Content
from core import db
from core import Node, NodeAlias
from contenttypes import Collections
from workflow.workflow import Workflows
from werkzeug.datastructures import ImmutableMultiDict
from utils.url import build_url_from_path_and_params
from functools import wraps

q = db.query


logg = logging.getLogger(__name__)


def handle_json_request(req):
    s = []
    if req.params.get("cmd") == "get_list_smi":
        searchmaskitem_id = req.params.get("searchmaskitem_id")
        f = None
        g = None
        if searchmaskitem_id and searchmaskitem_id != "full":
            f = q(Node).get(searchmaskitem_id).getFirstField()
        if not f:  # All Metadata
            f = g = getMetadataType("text")
        s = [
            f.getSearchHTML(
                Context(
                    g,
                    value=req.params.get("query_field_value"),
                    width=174,
                    name="query" +
                    ustr(
                        req.params.get("fieldno")),
                    language=lang(req),
                    collection=q(Collections).get(
                        req.params.get("collection_id")),
                    user=users.getUserFromRequest(req),
                    ip=req.ip))]
    req.write(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
    return


DISPLAY_PATH = re.compile("/([-.~_/a-zA-Z0-9]+)$")
known_node_aliases = {}


def change_language_request(req):
    language = req.args.get("change_language")
    if language:
        # only change session lang if language is configured
        if language in config.languages:
            req.session["language"] = language
        params = req.args.copy()
        del params["change_language"]
        req.request["Location"] = build_url_from_path_and_params(req.path, params)
        return httpstatus.HTTP_MOVED_TEMPORARILY


def check_change_language_request(func):
    @wraps(func)
    def checked(req):
        change_lang_http_status = change_language_request(req)
        if change_lang_http_status:
            return change_lang_http_status

        return func(req)

    return checked


@check_change_language_request
def display_404(req):
    return httpstatus.HTTP_NOT_FOUND


def overwrite_id_in_req(nid, req):
    """Patches a GET request to include a new nid.
    XXX: A bit hacky, nid handling should be changed somehow.
    """
    assert req.method == "GET"
    req.args = ImmutableMultiDict(dict(req.args, id=nid))
    req.params["id"] = nid
    return req


@check_change_language_request
def display_alias(req):
    match = DISPLAY_PATH.match(req.path)
    if match:
        alias_name = match.group(1).rstrip("/").lower()
        node_alias = q(NodeAlias).get(unicode(alias_name))

        if node_alias is not None:
            new_nid = node_alias.nid
        else:
            # -1 is a node ID that's never found, this will just display 404
            new_nid = -1

        req = overwrite_id_in_req(new_nid, req)
        # redirect to regular display handler
        display(req)
    else:
        raise RuntimeError(u"illegal alias '{}', should not be passed to this handler!".format(alias_name))


RE_NEWSTYLE_NODE_URL = re.compile("/(nodes/)?(\d+).*")


@check_change_language_request
def display_newstyle(req):
    """Handles requests for new style frontend node URLs matching
    /nodes/<nid> OR
    /<nid> (can be interpreted as alias, too)
    """
    nodes_path, nid_or_alias = RE_NEWSTYLE_NODE_URL.match(req.path).groups()
    if nodes_path is None:
        # check first if nid_or_alias is an alias
        maybe_node_alias = q(NodeAlias).get(unicode(nid_or_alias))
        if maybe_node_alias is not None:
            # found matching alias, assume it's an alias
            return display_alias(req)

    # either coming from /nodes/ or nid_or_alias is not a valid alias
    req = overwrite_id_in_req(nid_or_alias, req)
    return display(req)


@check_change_language_request
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
        mask = mdt.getMask(u'head_meta') if mdt is not None else None
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


@check_change_language_request
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


@check_change_language_request
def publish(req):
    m = PUBPATH.match(req.path)

    node = workflow_root = q(Workflows).one()
    if m:
        for a in m.group(2).split("/"):
            if a:
                node = node.children.filter_by(name=a).scalar()
                if node is None:
                    return 404

    req = overwrite_id_in_req(node.id, req)

    content = getContentArea(req)
    content.content = ContentNode(node)
    req.session["area"] = "publish"

    return display_noframe(req)


@check_change_language_request
def show_parent_node(req):
    parent = None
    node = q(Node).get(req.params.get("id"))
    if node is None:
        return display_noframe(req)

    for p in node.parents:
        if p.type != "directory" and p.type != "collection":
            parent = p
    if not parent:
        return display_noframe(req)

    req.params["id"] = parent.id
    req.params["obj"] = str(node.id)

    content = getContentArea(req)
    content.content = ContentNode(parent)

    return display_noframe(req)


def esc(v):
    return v.replace("\\", "\\\\").replace("'", "\\'")
