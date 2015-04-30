#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details


"""
from functools import partial
import logging
import os.path
import configargparse

from web.services.test.nodeiteration import visit_all_nodes
from utils.clients.api.access import MediatumAPISession


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARN)

logg = logging.getLogger(os.path.basename(__file__))


p = configargparse.ArgParser()
p.add("-b", "--base-uri")
p.add("-m", "--mask", default="default")
p.add("-c", "--command", default="get_node")
p.add("-s", "--skip", type=int, default=0, help="skip N nodes")

opts = p.parse_args()

api = MediatumAPISession(opts.base_uri or None, stream=False)
logg.info("using service base uri %s", api.url)

if opts.command == "get_node":
    logg.info("fetching all nodes with attributes")
    cmd = api.get_node

elif opts.command == "get_nodemask":
    logg.info("fetching mask %s", opts.mask)
    cmd = partial(api.get_nodemask, mask=opts.mask)
    
with api.session_context() as s:    
    sess = s
    visited_nids, exceptions = visit_all_nodes(api, get_func=cmd, start=opts.skip)