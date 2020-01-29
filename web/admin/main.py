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
import os
import codecs
import operator as _operator
import socket as _socket
import contextlib as _contextlib
import functools as _functools
import json as _json
try:
    import uwsgi as _uwsgi
except ImportError:
    _uwsgi = None

import core
import mediatumtal.tal as _tal
import core.request_handler as _core_request_handler
import core.webconfig as _core_webconfig
from core import config
from core.users import get_guest_user
from core import httpstatus
from utils.utils import join_paths, Menu
from web.admin.adminutils import findmodule, show_content, adminNavigation, getMenuItemID
from core.users import user_from_session as _user_from_session


logg = logging.getLogger(__name__)


def show_node(req):
    """ opens administration window with content """

    p = req.path[1:].split("/")
    style = req.params.get("style", u"")
    user = _user_from_session()

    v = {}
    v["user"] = user
    v["guestuser"] = get_guest_user().login_name
    v["version"] = core.__version__
    v["content"] = show_content(req, p[0])
    v["navigation"] = adminNavigation()
    v["breadcrumbs"] = getMenuItemID(v["navigation"], req.path[1:])

    spc = [
        Menu("sub_header_frontend", u"/"),
        Menu("sub_header_server_status", u"/admin/serverstatus/", target="_blank"),
        Menu("sub_header_edit", u"/edit"),
        Menu("sub_header_logout", u"/logout")
    ]

    if user.is_workflow_editor:
        spc.append(Menu("sub_header_workflow", u"../publish/"))

    v["spc"] = spc

    if len(p) > 0:
        if style == "":
            req.response.set_data(_tal.processTAL(v, file="web/admin/frame.html", macro="frame", request=req))
        else:
            req.response.set_data(v["content"])


def export(req):
    user = _user_from_session()
    """ export definition: url contains /[type]/[id] """

    if not user.is_admin:
        return httpstatus.HTTP_FORBIDDEN

    path = req.path[1:].split("/")
    module = findmodule(path[1])
    try:
        xml_result = module.export(req, path[2])
    except AttributeError as err:
        req.response.status_code = httpstatus.HTTP_NOT_FOUND
        _core_request_handler.error(req, httpstatus.HTTP_NOT_FOUND, str(err))

    req.response.status_code = httpstatus.HTTP_OK
    req.response.mimetype = "application/xml"
    req.response.set_data(xml_result)


def _meminfo():
    """
    :return:
    dict contains info from /proc/meminfo
    """
    meminfo = dict()
    with open('/proc/meminfo') as file:
        for line in file:
            key, value = line.split(":")
            key = key.strip()
            if key == 'MemFree' or key == 'MemTotal':
                value = int(value.strip()[:-2])
                meminfo[key] = value
    meminfo['prozent'] = int(round(float(meminfo['MemFree'])/float(meminfo['MemTotal']), 2)*100)
    return meminfo


def stats_server(req):
    """
    :param req:
    :return:
    - workers status provided by uwsgi
    - meminfo from /proc/meminfo
    - os.statvfs on uploaddir, tempdir and root
    """

    def get_info(data):
        free = (data.f_bavail * data.f_frsize)
        total = (data.f_blocks * data.f_frsize)
        used = (data.f_blocks - data.f_bfree) * data.f_frsize
        used_percent = int(round(100 - (100.0 * free / total)))
        _data = {"used": round(float(used)/2**30, 2), "total": round(float(total)/2**30, 2), "used_percent": used_percent}
        return _data

    user = _user_from_session()
    if not user.is_admin:
        return _core_request_handler.error(req, httpstatus.HTTP_FORBIDDEN, "<pre>You have not required rights</pre>")

    if _uwsgi:
        if "stats" in _uwsgi.opt:
            stats_server = _uwsgi.opt["stats"]
            workers = ""
            with _contextlib.closing(_socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)) as sock:
                try:
                    sock.connect(stats_server)
                    for data in iter(_functools.partial(sock.recv, 1024), ""):
                        workers += data
                    workers = _json.loads(workers)
                    workers = workers["workers"]
                except _socket.error as msg:
                    _core_request_handler.error(req, httpstatus.HTTP_INTERNAL_SERVER_ERROR, "<pre>" + str(msg) + "</pre>")
        else:
            workers = _uwsgi.workers()
        workers_without_cores = map(_operator.itemgetter("id", "pid", "requests", "delta_requests", "exceptions",
                                                         "signals", "status", "rss", "running_time", "last_spawn",
                                                         "respawn_count", "avg_rt"), workers)
        keys = "id", "pid", "requests", "delta_requests", "exceptions", "signals", "status", \
               "rss", "running_time", "last_spawn", "respawn_count", "avg_rt"
        workers_without_cores = map(lambda worker: zip(keys, worker), workers_without_cores)
        if workers[0].has_key("cores"):
            workers_cores = map(_operator.itemgetter("cores"), workers)
            workers_vars = lambda worker_cores: map(_operator.itemgetter("vars"), worker_cores)
            workers_vars = map(workers_vars, workers_cores)

            remote_addrs = lambda worker_vars: filter(lambda x: x.startswith("REMOTE_ADDR"), worker_vars)
            remote_addrs = map(lambda worker_vars: map(remote_addrs, worker_vars), workers_vars)
            break_line = lambda remote_addrs: map(lambda remote_addrs: "<br>".join(remote_addrs), remote_addrs)
            remote_addrs = map(break_line, remote_addrs)
            remote_addrs = map(lambda remote_addrs: remote_addrs[0], remote_addrs)
            remote_addrs = map(lambda remote_addr: remote_addr.split("=")[1] if "=" in remote_addr else remote_addr, remote_addrs)
            remote_addrs = map(lambda remote_addr: ("remote_addr",remote_addr), remote_addrs)
            for i in range(len(workers_without_cores)):
                workers_without_cores[i].append(remote_addrs[i])

            request_uris = lambda worker_vars: filter(lambda x: x.startswith("REQUEST_URI"), worker_vars)
            request_uris = map(lambda worker_vars: map(request_uris, worker_vars), workers_vars)
            break_line = lambda request_uris: map(lambda request_uris: "<br>".join(request_uris), request_uris)
            get_worker_request_uris = map(break_line, request_uris)
            request_uris = map(lambda request_uris: request_uris[0], get_worker_request_uris)
            request_uris = map(lambda request_uri: request_uri.split("=")[1] if "=" in request_uri else request_uri, request_uris)
            request_uris = map(lambda request_uri: ("request_uri", request_uri), request_uris)
            for i in range(len(workers_without_cores)):
                workers_without_cores[i].append(request_uris[i])
        else:
            for i in range(len(workers_without_cores)):
                if i==0:
                    workers_without_cores[i].append(("remote_addr", "uwsgi stats server not available"))
                else:
                    workers_without_cores[i].append(("remote_addr", ""))
                workers_without_cores[i].append(("request_uri", ""))
    else:
        workers_without_cores = "Application is not running under uwsgi"

    meminfo = _meminfo()
    total = meminfo['MemTotal']*1024
    free = meminfo['MemFree']*1024
    used = total - free
    used_percent = int(round(100-(100.0*free/total)))
    meminfo = {"used": round(float(used)/2**30, 2), "total": round(float(total)/2**30, 2), "used_percent": used_percent}

    datadir = config.get("paths.datadir")
    uploadmem = get_info(os.statvfs(datadir))

    tempdir = config.get("paths.tempdir")
    tempdirmem = get_info(os.statvfs(tempdir))

    rootmem = get_info(os.statvfs("/"))

    ctx = {"workers": workers_without_cores, "meminfo": meminfo, "tempdirmem": tempdirmem,
           "rootmem": rootmem, "uploadmem": uploadmem, "datadir": datadir, "tempdir": tempdir}
    html = _core_webconfig.theme.render_template("server_status.j2.jade", ctx)
    req.response.set_data(html)
    req.response.status_code = httpstatus.HTTP_OK
