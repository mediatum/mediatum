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
from core import db
from core.translation import t
from contenttypes import Data
from sqlalchemy.orm.exc import NoResultFound

q = db.query

logg = logging.getLogger(__name__)


def export(req):
    p = req.path[1:].split("/")

    if len(p) != 2:
        req.error(404, "Object not found")
        return

    if p[0].isdigit():
        try:
            node = q(Data).get(p[0])
        except:
            return req.error(404, "Object not found")
    else:
        return req.error(404, "Object not found")

    if not node.has_read_access():
        req.write(t(req, "permission_denied"))
        return

    mask = node.metadatatype.getMask(p[1])
    if mask:
        try:
            req.reply_headers['Content-Type'] = "text/plain; charset=utf-8"
            req.write(mask.getViewHTML([node], flags=8))  # flags =8 -> export type
        except NoResultFound:
            return req.error(404, "Object not found")
    else:
        req.error(404, "Object not found")
        return
