"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>

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

from contenttypes import Data
from core import db
from utils.utils import getFormatedString

q = db.query

def getContent(req, ids):
    node = q(Data).get(long(ids[0]))

    if hasattr(node, "show_node_big"):
        return req.getTAL("web/edit/modules/view.html", {'content': getFormatedString(node.show_node_big(req))}, macro="view_node")
    else:
        return req.getTAL("web/edit/modules/view.html", {}, macro="view_noview")
