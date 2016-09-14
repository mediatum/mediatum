"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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
from core.transition import current_user
from contenttypes import Container, Content

from .ftreedata import getData, getPathTo, getLabel

q = db.query
logg = logging.getLogger(__name__)


def ftree(req):

    if not current_user.is_editor:
        logg.warn("ftree permission denied for user: %s", current_user.id)
        return 403

    if "parentId" in req.params:
        return getData(req)

    if "pathTo" in req.params:
        return getPathTo(req)

    if "getLabel" in req.params:
        return getLabel(req)

    if "changeCheck" in req.params:
        for id in req.params.get("currentitem").split(","):
            node = q(Content).get(id)
            parent = q(Container).get(req.params.get("changeCheck"))
            if not(node and parent and node.has_write_access() and parent.has_write_access()):
                logg.warn("illegal ftree request: %s", req.params)
                return 403

            if node in parent.content_children:
                if len(node.parents) > 1:
                    parent.content_children.remove(node)
                    logg.info("ftree change ")
                    db.session.commit()
                else:
                    req.writeTALstr('<tal:block i18n:translate="edit_classes_noparent"/>', {})
            else:
                parent.content_children.append(node)
                db.session.commit()