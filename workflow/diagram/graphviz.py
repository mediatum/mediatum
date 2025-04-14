# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import httplib as _httplib
import logging
import os.path
from pydot import Node, Edge, Dot
import core.config as config
from ..workflow import getWorkflow
from core.request_handler import sendFile as _sendFile
from core.users import user_from_session as _user_from_session
import utils as _utils
import utils.utils as _

logg = logging.getLogger(__name__)


def add_node_rec(node, workflow, g, known_nodes):
    """
    Recurses through the workflow graph and adds nodes and edges.
    Repeated nodes are ignored (cycle detection).
    """
    name = node.getName()
    if name in known_nodes:
        return known_nodes[name]
    dot_node = Node(name=name)
    g.add_node(dot_node)
    known_nodes[name] = dot_node
    logg.debug("created node %s", name)
    try:
        true_next_id = node.getTrueId()
    except:
        true_next_id = None
    if true_next_id:
        true_next = workflow.getStep(true_next_id)
        true_dot_next = add_node_rec(true_next, workflow, g, known_nodes)
        true_label = node.getTrueLabel() or " "
        g.add_edge(Edge(dot_node, true_dot_next, color="darkgreen",label=true_label))
        logg.debug("created True edge: %s -> %s", name, true_next_id)
    try:
        false_next_id = node.getFalseId()
    except:
        false_next_id = None
    if false_next_id:
        false_next = workflow.getStep(false_next_id)
        false_dot_next = add_node_rec(false_next, workflow, g, known_nodes)
        false_label = node.getFalseLabel() or " "
        g.add_edge(Edge(dot_node, false_dot_next, color="red", label=false_label))
        logg.debug("created False edge: %s -> %s", name, false_next_id)

    if not (true_next_id or false_next_id):
        # end node with no connections
        dot_node.set("color", "#04B45F")
    return dot_node


def send_workflow_diagram(req):
    """Delivers workflow image, pdf or dot code to client.
    """
    user = _user_from_session()
    if not user.is_admin:
        return _httplib.FORBIDDEN
    workflow = getWorkflow(req.params.get("wid", ""))
    known_nodes = {}
    start = workflow.getStartNode()
    name = workflow.getName()
    graph = Dot(graph_name=name, ranksep=1,
                labelloc="t", label="workflow: " + name, fontsize=18, fontcolor="blue")
    graph.set_node_defaults(shape="box", fontsize=12)
    graph.set_edge_defaults(fontsize=13, labeldistance=3)

    # traverse from start node
    add_node_rec(start, workflow, graph, known_nodes)

    filename = _utils.utils.new_temp_download_file("{}.png".format(workflow.getName()))
    graph.write_png(filename)
    _sendFile(req, filename, "image/png")
