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
from core import config as _core_config

logg = logging.getLogger(__name__)

urls = {
    "/node/(?P<id>\d+)/{0,1}$": handlers.get_node_single,
    "/node/(?P<id>\d+)/children/{0,1}$": handlers.get_node_children,
    "/node/(?P<id>\d+)/allchildren/{0,1}$": handlers.get_node_allchildren,
    "/node/(?P<id>\d+)/parents/{0,1}$": handlers.get_node_parents,
}

request_count = 0


def request_handler(req):
    global request_count

    handle_starttime = time.time()
    matched = False
    req_path = req.mediatum_contextfree_path
    for pattern, handler_func in urls.iteritems():
        m = re.match(pattern, req_path)
        if m:
            matched = True
            response_code, s, d, content_type = handler_func(
                    req.path,
                    req.query_string,
                    req.host_url,
                    req.values,
                    **m.groupdict()
                )
            break

    if not matched:
        req.response.set_data(response_code_dict[400])
        req.response.status_code = 400
        return

    disposition = req.values.get('disposition', '')
    if disposition:
        req.response.headers['Content-Disposition'] = disposition
    if 'deflate' in req.values:
        req.response.content_encoding = "deflate"
    elif 'gzip' in req.values:
        req.response.content_encoding = "gzip"

    req.response.set_data(s)
    req.response.content_type = content_type
    req.response.content_length = len(s)
    if _core_config.getboolean("services.allow_cross_origin", False):
        req.response.headers['Access-Control-Allow-Origin'] = '*'

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
    bytes_sent = len(s)
    s = "services {} '{}' ({}): {} for {} bytes for service request no. {} ({}, {}, {}) - (user-agent: {})".format(
            req.remote_addr,
            ustr(response_code),
            response_code_description,
            handle_duration,
            bytes_sent,
            request_count,
            req.method,
            "{}{}".format(req.path, req.query_string or ''),
            req.params,
            useragent,
        )

    if logg.isEnabledFor(logging.INFO) and matched and 'timetable' in d:
        timesum = 0.0
        s += "\n| timetable for request ({}, {}, {})".format(req.method, req.path, req.values)
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
