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
from functools import partial, wraps
import logging
import re
from werkzeug.datastructures import ImmutableMultiDict

import core.config as config
from core.metatype import Context
from core.translation import lang, switch_language
from core.transition import httpstatus
from core import db
from core import Node, NodeAlias
from core.transition import current_user
from contenttypes import Container
from schema.schema import getMetadataType
from utils.url import build_url_from_path_and_params
from web.frontend.frame import render_page
from web.frontend.content import render_content
from workflow.workflow import Workflows
from core.nodecache import get_collections_node

q = db.query


logg = logging.getLogger(__name__)


def handle_json_request(req):
    s = []
    if req.args.get("cmd") == "get_list_smi":
        searchmaskitem_id = req.params.get("searchmaskitem_id")
        f = None
        g = None
        if searchmaskitem_id and searchmaskitem_id != "full":
            f = q(Node).get(searchmaskitem_id).getFirstField()
        if not f:  # All Metadata
            f = g = getMetadataType("text")

        container_id = req.args.get("container_id")

        container = q(Container).get(container_id) if container_id else None

        if container is None or not container.has_read_access():
            container = get_collections_node()

        s = [
            f.getSearchHTML(
                Context(
                    g,
                    value=req.args.get("query_field_value"),
                    width=174,
                    name="query" + str(req.args.get("fieldno")),
                    language=lang(req),
                    container=container,
                    user=current_user,
                    ip=req.ip))]
    req.write(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))


DISPLAY_PATH = re.compile("/([_a-zA-Z][_/a-zA-Z0-9]+)$")
known_node_aliases = {}


def change_language_request(req):
    language = req.args.get("change_language")
    if language:
        # change language cookie if language is configured
        switch_language(req, language)
        params = req.args.copy()
        del params["change_language"]
        req.request["Location"] = build_url_from_path_and_params(req.path, params)
        # set the language cookie for caching
        req.setCookie("language", language)
        return httpstatus.HTTP_MOVED_TEMPORARILY


def check_change_language_request(func):
    @wraps(func)
    def checked(req, *args, **kwargs):
        change_lang_http_status = change_language_request(req)
        if change_lang_http_status:
            return change_lang_http_status

        return func(req, *args, **kwargs)

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
        raise RuntimeError(u"illegal alias '{}', should not be passed to this handler!".format(req.path))


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
    return _display(req)


@check_change_language_request
def _display(req, show_navbar=True, render_paths=True, params=None):
    if "jsonrequest" in req.params:
        return handle_json_request(req)

    if params is None:
        params = req.args

    nid = params.get("id", type=int)
    
    if nid is None:
        node = get_collections_node()
    else:
        node = q(Node).prefetch_attrs().prefetch_system_attrs().get(nid)
        
    if node is not None and not node.has_read_access():
        node = None
        
    if req.args.get("disable_content"):
        content_html = u""
    else:
        content_html = render_content(node, req, render_paths)

    if params.get("raw"):
        req.write(content_html)
    else:
        html = render_page(req, node, content_html, show_navbar)
        req.write(html)
    # ... Don't return a code because Athana overwrites the content if an http error code is returned from a handler.
    # instead, req.setStatus() can be used in the rendering code


@check_change_language_request
def display(req):
    _display(req)


@check_change_language_request
def workflow(req):
    if req.method == "POST":
        params = req.form
    else:
        params = req.args

    _display(req, show_navbar=False, render_paths=False, params=params)


#: needed for workflows:
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
    return _display(req, False, render_paths=False)


@check_change_language_request
def show_parent_node(req):
    parent = None
    node = q(Node).get(req.params.get("id"))
    if node is None:
        return workflow(req)

    for p in node.parents:
        if not isinstance(p, Container):
            parent = p
    if not parent:
        return workflow(req)

    req = overwrite_id_in_req(parent.id, req)
    req.params["obj"] = str(node.id)

    return workflow(req)
