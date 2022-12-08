# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import sys
import re
import time
import logging
import BaseHTTPServer

response_code_dict = BaseHTTPServer.BaseHTTPRequestHandler.responses

from . import handlers

logg = logging.getLogger(__name__)

SERVICES_URL_HAS_HANDLER = 1
SERVICES_URL_SIMPLE_REWRITE = 2

urls = [
    ["GET", "/node/(?P<id>\d+)/{0,1}$", handlers.get_node_single, None, SERVICES_URL_HAS_HANDLER, None],
    ["GET", "/node/(?P<id>\d+)/children/{0,1}$", handlers.get_node_children, None, SERVICES_URL_HAS_HANDLER, None],
    ["GET", "/node/(?P<id>\d+)/allchildren/{0,1}$", handlers.get_node_allchildren, None, SERVICES_URL_HAS_HANDLER, None],
    ["GET", "/node/(?P<id>\d+)/parents/{0,1}$", handlers.get_node_parents, None, SERVICES_URL_HAS_HANDLER, None],
]

request_count = 0


def request_handler(req):
    global request_count

    handle_starttime = time.time()
    matched = False
    req_path = req.mediatum_contextfree_path

    for method, pattern, handler_func, rewrite_target, url_flags, data in urls:
        if method and method == req.method:
            m = re.match(pattern, req_path)
            if m:

                matched = True

                if url_flags == SERVICES_URL_HAS_HANDLER:
                    handle_path = req.mediatum_contextfree_path
                    handle_params = req.params
                    response_code, bytes_sent, d = handler_func(req, handle_path, handle_params, data, **m.groupdict())
                    break

                if url_flags == SERVICES_URL_SIMPLE_REWRITE:
                    handle_path = rewrite_target[0]

                    handle_params = req.params.copy()
                    for key, value in rewrite_target[1].items():
                        handle_params[key] = value

                    argsdict = m.groupdict().copy()
                    for key, value in rewrite_target[2].items():
                        argsdict[key] = value

                    response_code, bytes_sent, d = handler_func(req, handle_path, handle_params, data, **argsdict)
                    break

    if not matched:
        req.response.set_data(response_code_dict[400])
        req.response.status_code = 400
        return

    handle_endtime = time.time()
    handle_duration = "%.3f sec." % (handle_endtime - handle_starttime)

    response_code_description = response_code_dict[int(response_code)][0]

    useragent = 'unknown'
    try:
        cutoff = 60
        useragent = req.headers['user-agent']
        if len(useragent) > cutoff:
            useragent = useragent[0:cutoff] + '...'
    except:
        pass

    request_count += 1
    req_query = req.query_string
    if not req_query:
        req_query = ''
    s = "services {} '{}' ({}): {} for {} bytes for service request no. {} ({}, {}, {}) - (user-agent: {})".format(
            req.remote_addr,
            ustr(response_code),
            response_code_description,
            handle_duration,
            bytes_sent,
            request_count,
            req.method,
            req.path + req_query,
            req.params,
            useragent,
        )

    if logg.isEnabledFor(logging.INFO) and matched and 'timetable' in d:
        timesum = 0.0
        s += "\n| timetable for request (%s, %s, %s)" % (req.method, req.path, handle_params)
        for i, timetable_step in enumerate(d['timetable']):
            if len(timetable_step) == 2:
                step, executiontime = timetable_step
            elif len(timetable_step) == 1:
                step = timetable_step[0]
                executiontime = 0.0
            else:
                continue
            s += "\n|  %2d. step: %.3f sec.: %s" % (i, executiontime, step)
            timesum += executiontime
        s += "\n| sum of execution times: {} sec.:{} bytes returned".format(timesum, bytes_sent)
        logg.info("%s", s)
    else:
        logg.info("%s", s)
    sys.stdout.flush()

    return response_code
