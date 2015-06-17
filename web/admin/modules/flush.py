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

import core.webconfig as webconfig
from web.admin.adminutils import getAdminStdVars


logg = logging.getLogger(__name__)


def getInformation():
    return{"version": "1.0"}


def validate(req, op):

    if "op" in req.params.keys():
        if req.params.get("op") == "flushall":
            webconfig.flush(req)
            req.writeTAL("web/admin/modules/flush.html", {}, macro="flushed")
            return ""
    else:
        for key in req.params.keys():

            if key.startswith("flush_db"):
                logg.info("flush db")
                # tree.flush()
                op = "db"
                return view(req, op)

            # if key.startswith("flush_all"):
            #    print "flush all"
            #    op = "all"
            #    return view(req, op)
    return view(req, op)


def view(req, op):
    v = getAdminStdVars(req)

    v["msg"] = ""
    v["op"] = op
    if op == "db":
        v["msg"] = "admin_flush_data_cleared"
    # elif op == "all":
    #    v["msg"] = "admin_flush_all_cleared"
    return req.getTAL("web/admin/modules/flush.html", v, macro="view")
