"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner Neudenberger <neudenberger@ub.tum.de>


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
import re
import time
import locale
import BaseHTTPServer

response_code_dict = BaseHTTPServer.BaseHTTPRequestHandler.responses

LOCALES = ["en_US.UTF-8", "english", "german"]

try:
    locale.setlocale(locale.LC_ALL, LOCALES[0])  # for thousands separator
except:
    pass

try:
    locale.setlocale(locale.LC_ALL, LOCALES[1])  # for thousands separator
except:
    pass

from . import handlers

SERVICES_URL_HAS_HANDLER = 1
SERVICES_URL_SIMPLE_REWRITE = 2

urls = [["GET",
         "/index.html$",
         handlers.serve_file,
         ("/static/index.html",
          {},
          {'filepath': 'index.html'}),
         SERVICES_URL_SIMPLE_REWRITE,
         None],
        ["GET",
         "/upload.html$",
         handlers.serve_file,
         ("/static/upload.html",
          {},
             {'filepath': 'upload.html'}),
         SERVICES_URL_SIMPLE_REWRITE,
         None],
        ["GET",
         "/calcsign$",
         handlers.calcsign,
         None,
         SERVICES_URL_HAS_HANDLER,
         None],
        ["GET",
         "/$",
         handlers.serve_file,
         ("/static/index.html",
          {},
             {'filepath': 'index.html'}),
         SERVICES_URL_SIMPLE_REWRITE,
         None],
        ["POST",
         "/new$",
         handlers.upload_new_node,
         None,
         SERVICES_URL_HAS_HANDLER,
         None],
        ["POST",
         "/update/(?P<id>\d+)/{0,1}$",
         handlers.update_node,
         None,
         SERVICES_URL_HAS_HANDLER,
         None],
        ]


def request_handler(req):

    handle_starttime = time.time()
    response_code = 403
    matched = False
    req_path = req.path
    for method, pattern, handler_func, rewrite_target, url_flags, data in urls:
        if method and method == req.command:
            m = re.match(pattern, req_path)
            if m:

                matched = True

                if url_flags == SERVICES_URL_HAS_HANDLER:
                    handle_path = req.path
                    handle_params = req.params
                    response_code, bytes_sent, d = handler_func(
                        req, handle_path, handle_params, data, **m.groupdict())
                    break

                if url_flags == SERVICES_URL_SIMPLE_REWRITE:
                    handle_path = rewrite_target[0]

                    handle_params = req.params.copy()
                    for key, value in rewrite_target[1].items():
                        handle_params[key] = value

                    argsdict = m.groupdict().copy()
                    for key, value in rewrite_target[2].items():
                        argsdict[key] = value

                    response_code, bytes_sent, d = handler_func(
                        req, handle_path, handle_params, data, **argsdict)
                    break

    # try to call default handler, if no match
    if not matched:
        try:
            if getattr(handlers, 'default_handler'):
                response_code, bytes_sent = handlers.default_handler(req)
        except:
            response_code, bytes_sent = '404', 0

    if not matched:
        return req.error(404, "File %s not found" % req.path)

    return response_code
