# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import json
from functools import partial, wraps
import logging
import re
import flask as _flask
from werkzeug.datastructures import ImmutableMultiDict
import werkzeug.utils as _werkzeug_utils

import core.config as config
import core.csrfform as _core_csrfform
import core.translation as _core_translation
from core import httpstatus
from core import db
from core import Node, NodeAlias
import core.nodecache as _nodecache
from core.users import user_from_session as _user_from_session
from contenttypes import Container
from schema.schema import getMetadataType
from utils.url import build_url_from_path_and_params
from web.frontend.frame import render_page
from web.frontend.content import render_content
from workflow.workflow import Workflows
from core.nodecache import get_collections_node

q = db.query


logg = logging.getLogger(__name__)


def _handle_json_request(req):
    user = _user_from_session()
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
                container,
                g,
                _core_translation.set_language(req.accept_languages),
                "query" + str(req.args.get("fieldno")),
                req.args.get("query_field_value"),
            )]
    req.response.set_data(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
    req.response.status_code = httpstatus.HTTP_OK


DISPLAY_PATH = re.compile("/([_a-zA-Z][_/a-zA-Z0-9]+)$")
known_node_aliases = {}


def _check_change_language_request(func):
    @wraps(func)
    def checked(req, *args, **kwargs):
        language = req.args.get("change_language")
        if language:
            # change language cookie if language is configured
            _core_translation.set_language(req.accept_languages, language)
            params = req.args.copy()
            del params["change_language"]
            req.response.location = build_url_from_path_and_params(req.mediatum_contextfree_path, params)
            # set the language cookie for caching

        return func(req, *args, **kwargs)

    return checked


@_check_change_language_request
def display_404(req):
    req.response.status_code = httpstatus.HTTP_NOT_FOUND
    return httpstatus.HTTP_NOT_FOUND


def overwrite_id_in_req(nid, req):
    """Patches a GET request to include a new nid.
    XXX: A bit hacky, nid handling should be changed somehow.
    """
    assert req.method == "GET"
    req.args = ImmutableMultiDict(dict(req.args, id=nid))
    req.params["id"] = nid
    req.__dict__["values"] = _werkzeug_utils._missing
    return req


@_check_change_language_request
def display_alias(req):
    match = DISPLAY_PATH.match(req.mediatum_contextfree_path)
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
        raise RuntimeError(u"illegal alias '{}', should not be passed to this handler!".format(req.mediatum_contextfree_path))


RE_NEWSTYLE_NODE_URL = re.compile("/(nodes/)?(\d+).*")


@_check_change_language_request
def display_newstyle(req):
    """Handles requests for new style frontend node URLs matching
    /nodes/<nid> OR
    /<nid> (can be interpreted as alias, too)
    """
    nodes_path, nid_or_alias = RE_NEWSTYLE_NODE_URL.match(req.mediatum_contextfree_path).groups()
    if nodes_path is None:
        # check first if nid_or_alias is an alias
        maybe_node_alias = q(NodeAlias).get(unicode(nid_or_alias))
        if maybe_node_alias is not None:
            # found matching alias, assume it's an alias
            return display_alias(req)

    # either coming from /nodes/ or nid_or_alias is not a valid alias
    req = overwrite_id_in_req(nid_or_alias, req)
    return display(req)


@_check_change_language_request
def display(req, show_navbar=True, render_paths=True, params=None):
    if "jsonrequest" in req.params:
        return _handle_json_request(req)

    if params is None:
        params = req.args

    node = params.get("id", type=int)
    node = (get_collections_node() if node is None else
            q(Node).prefetch_attrs().prefetch_system_attrs().get(node))
    if not (node and node.has_read_access()):
        node = None

    if req.args.get("disable_content"):
        content_html = u""
        show_id = None
    else:
        content_html, show_id = render_content(node, req, render_paths)
    req.response.set_data(content_html if params.get("raw") else
                          render_page(req, content_html, node, show_navbar, show_id))
    req.response.status_code = httpstatus.HTTP_OK


@_check_change_language_request
def workflow(req):
    if req.method == "POST":
        _core_csrfform.validate_token(req.form)
    display(req, False, False, req.values)


#: needed for workflows:
PUBPATH = re.compile("/?(publish|pub)/(.*)$")

@_check_change_language_request
def publish(req):
    if req.method == "POST":
        _core_csrfform.validate_token(req.form)

    m = PUBPATH.match(req.mediatum_contextfree_path)

    node = _nodecache.get_workflows_node()
    if m:
        for a in m.group(2).split("/"):
            if a:
                node = node.children.filter_by(name=a).scalar()
                if node is None:
                    return 404

    return display(overwrite_id_in_req(node.id, req), False, False)


@_check_change_language_request
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
    req.args = ImmutableMultiDict(dict(req.args, obj=str(node.id)))
    req.params["obj"] = req.args["obj"]

    return workflow(req)
