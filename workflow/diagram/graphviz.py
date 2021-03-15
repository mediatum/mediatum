# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2013 Tobias Stenzel <tobias.stenzel@tum.de>

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
from __future__ import division

import logging
import os.path
from pydot import Node, Edge, Dot
import core.config as config
from ..workflow import getWorkflow
from core import httpstatus as _httpstatus
from core.request_handler import sendFile as _sendFile
from core.users import user_from_session as _user_from_session

logg = logging.getLogger(__name__)


FILE_ENDINGS = {
    "png": ".png",
    "svg": ".svg",
    "dot": ".dot",
    "pdf": ".pdf",
}


def true_edge(n_src, n_dest, **kwargs):
    """Returns an edge with default settings for a 'true' edge"""
    return Edge(n_src, n_dest, color="darkgreen", **kwargs)  # blue


def false_edge(n_src, n_dest, **kwargs):
    """Returns an edge with default settings for a 'false' edge"""
    return Edge(n_src, n_dest, color="red", **kwargs)  # darkorange


class GraphvizWorkflowDiagram(object):

    """Workflow diagram based on Graphviz.
    Can generate png and svg images, pdf documents and raw dot code.
    TODO: more media types
    """

    def __init__(self, workflow, output_dir=None):
        """
        Create 'Dot' visualization graph from workflow node.
        :type workflow: Workflow
        :param output_dir: dir for created files, use configured tmpdir if None
        """

        output_dir = output_dir or config.get("paths.tempdir")
        name = workflow.getName()
        self._filename = fn = os.path.join(output_dir, name)
        logg.info("creating workflow dot diagram for '%s', filename '%s.*'", name, fn)
        self.graph = self.create_graph_from_workflow(workflow)
        # TODO: cache images. We must find out if the workflow changed since the stored image was created.
        # maybe use attribute updatetime?. It is not set atm.
#         if not os.path.exists(fn):

    def render_png(self):
        """Writes png image to file"""
        self.graph.write_png(self._filename + ".png")
        return self

    def render_svg(self):
        """Writes svg image to file"""
        self.graph.write_svg(self._filename + ".svg")
        return self

    def render_pdf(self):
        """Writes pdf document to file"""
        self.graph.write_pdf(self._filename + ".pdf")
        return self

    def output_dot(self):
        """Writes dot code to file"""
        self.graph.write_raw(self._filename + ".dot")
        return self

    def filename(self, media_type="png"):
        """Returns file name for created file
        :param media_type: one of: 'png','svg', 'pdf', 'dot' (...)
        TODO: more media types
        """
        return self._filename + FILE_ENDINGS[media_type]

    def create_graph_from_workflow(self, workflow):
        """
        :type workflow: Workflow
        :rtype: Dot
        """
        known_nodes = {}
        start = workflow.getStartNode()
        name = workflow.getName()
        g = Dot(graph_name=name, ranksep=1,
                labelloc="t", label="workflow: " + name, fontsize=18, fontcolor="blue")
        g.set_node_defaults(shape="box", fontsize=12)
        g.set_edge_defaults(fontsize=13, labeldistance=3)

        def add_node_rek(node):
            """Recurses through the workflow graph and adds nodes and edges.
            Repeated nodes are ignored (cycle detection).
            :type node: core.tree.Node
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
                true_dot_next = add_node_rek(true_next)
                true_label = node.getTrueLabel() or " "
                g.add_edge(true_edge(dot_node, true_dot_next, label=true_label))
                logg.debug("created True edge: %s -> %s", name, true_next_id)
            try:
                false_next_id = node.getFalseId()
            except:
                false_next_id = None
            if false_next_id:
                false_next = workflow.getStep(false_next_id)
                false_dot_next = add_node_rek(false_next)
                false_label = node.getFalseLabel() or " "
                g.add_edge(false_edge(dot_node, false_dot_next, label=false_label))
                logg.debug("created False edge: %s -> %s", name, false_next_id)

            if not (true_next_id or false_next_id):
                # end node with no connections
                dot_node.set("color", "#04B45F")
            return dot_node
        # traverse from start node
        add_node_rek(start)
        return g


def send_workflow_diagram(req, media_type="png"):
    """Delivers workflow image, pdf or dot code to client.
    :param media_type: one of: 'png','svg', 'pdf', 'dot' (...)
    """
    user = _user_from_session()
    if not user.is_admin:
        return _httpstatus.HTTP_FORBIDDEN
    workflow = getWorkflow(req.params.get("wid", ""))
    diag = GraphvizWorkflowDiagram(workflow)
    if media_type == "png":
        diag.render_png()
        _sendFile(req, diag.filename(media_type), "image/png")
    elif media_type == "svg":
        diag.render_svg()
        _sendFile(req, diag.filename(media_type), "image/svg+xml")
    elif media_type == "pdf":
        diag.render_pdf()
        _sendFile(req, diag.filename(media_type), "application/pdf")
    elif media_type == "dot":
        diag.write_dot()
        _sendFile(req, diag.filename(media_type), "text/vnd.graphviz")
    else:
        raise ValueError("media type " + media_type + " not supported!")


def create_example_graph():
    g = Dot(graph_name="workflow: example",
            labelloc="t", label="workflow: example", fontsize=18, fontcolor="blue")
    g.set_node_defaults(shape="box", fontsize=12)
    g.set_edge_defaults(fontsize=13, labeldistance=3)
    n1 = Node(name="Start")
    g.add_node(n1)
    n2 = Node(name="StepTrueEnd", color="#04B45F")
    g.add_node(n2)
    n3 = Node(name="StepFalse")
    g.add_node(n3)
    n4 = Node(name="StepFalse2")
    g.add_node(n4)
    n5 = Node(name="StepFalse3End", color="#04B45F")
    g.add_node(n5)
    e1 = true_edge(n1, n2)
    g.add_edge(e1)
    e2 = false_edge(n1, n3)
    g.add_edge(e2)
    e3 = true_edge(n3, n4)
    g.add_edge(e3)
    e_back = false_edge(n4, n1, label="back if false")
    g.add_edge(e_back)
    e4 = true_edge(n4, n5)
    g.add_edge(e4)
    return g
