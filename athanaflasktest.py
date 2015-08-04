# coding: utf8
#! /usr/bin/env nix-shell
#! nix-shell -i python
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

import logging
import sys
import codecs
import pyaml
import yaml
from flask.app import Flask

logging.basicConfig()
logg = logging.getLogger(__name__)


### stackdump

import os
import threading
import traceback
try:
    import IPython.core.ultratb as ultratb
except:
    ultratb = None

if ultratb is None:
    logg.warn("IPython not installed, stack dumps not available!")
else:
    logg.info("IPython installed, write stack dumps to tmpdir with: `kill -QUIT <mediatum_pid>`")
    def dumpstacks(signal, frame):
        print "dumping stack"
        filepath = os.path.join("/tmp", "mediatum_threadstatus")
        id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
        full = ["-" * 80]
        tb_formatter = ultratb.ListTB(color_scheme="Linux")
        for thread_id, stack in sys._current_frames().items():
            thread_name = id2name.get(thread_id, "")
            if not "Main" in thread_name:
                stacktrace = traceback.extract_stack(stack)
                stb = tb_formatter.structured_traceback(Exception, Exception(), stacktrace)[8:-1]
                if stb:
                    formatted_trace = tb_formatter.stb2text(stb).strip()
                    with codecs.open("{}.{}".format(filepath, thread_id), "w", encoding='utf8') as wf:
                        wf.write("\n{}".format(formatted_trace))
                    if len(stb) > 4:
                        short_stb = stb[:2] + ["..."] + stb[-2:]
                    else:
                        short_stb = stb
                    formatted_trace_short = tb_formatter.stb2text(short_stb).strip()
                    full.append("# Thread: %s(%d)" % (thread_name, thread_id))
                    full.append(formatted_trace_short)
                    full.append("-" * 80)


        with codecs.open(filepath, "wf", encoding='utf8') as wf:
            wf.write("\n".join(full))

    import signal
    signal.signal(signal.SIGQUIT, dumpstacks)

from core import athana


### out web contexts

def hello(request):
    return 400



from core.init import add_ustr_builtin
add_ustr_builtin()


### simple WSGI app

def wsgi_app(environ, start_response):
    path = environ["PATH_INFO"].strip("/")
    response_headers = [("Content-type", "text/html")]

    if path == "hello":
        status = "200 OK"
        response_headers = [("Content-type", "text/plain")]
        start_response(status, response_headers)
        resp = ["Hello from WSGI!"]
        resp.extend('%s: %s' % (key, value) for key, value in sorted(environ.items()))
        return resp

    elif path == "umlaut":
        status = "200 OK"
        start_response(status, response_headers)
        return [u"Hellö fröm WßGI!"]

    elif path == "writetest":
        status = "200 OK"
        write_func = start_response(status, response_headers)
        write_func("blababalba")
        return ["return"]

    else:
        status = "404 Not Found"
        response_headers = [("Content-type", "text/html")]
        start_response(status, response_headers)
        return ["txt"]


athana.add_wsgi_context("/wsgi", wsgi_app)

### flask

flask_app = Flask("athanaflasktest")

@flask_app.route("/hello")
def flask_hello():
    return "Hello from Flask"

@flask_app.route("/param/<param>")
def flask_param(param):
    from flask import request
    return "url param was: {}, args: {}".format(param, request.args)

@flask_app.route("/umlaut")
def flask_umlaut():
    return "Hellö fröm Fläßk"


athana.add_wsgi_context("/flask", flask_app)


### internal athana handler

ctx = athana.addContext("/", ".")
fl = ctx.addFile("core/test/athanatesthandler.py")
fl.addHandler("hello").addPattern("/hello")


athana.setThreads(1)
athana.run(8080)
