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
from core import Node
from core import db

from .ftreedata import getData, getPathTo, getLabel

q = db.query
logg = logging.getLogger(__name__)


def ftree(req):
    if "parentId" in req.params:
        return getData(req)

    if "pathTo" in req.params:
        return getPathTo(req)

    if "getLabel" in req.params:
        return getLabel(req)

    if "changeCheck" in req.params:
        try:
            for id in req.params.get("currentitem").split(","):
                node = q(Node).get(id)
                parent = q(Node).get(req.params.get("changeCheck"))
                if node in parent.children:
                    if len(node.parents) > 1:
                        parent.children.remove(node)
                        db.session.commit()
                    else:
                        req.writeTALstr('<tal:block i18n:translate="edit_classes_noparent"/>', {})
                else:
                    parent.children.add(node)
                    db.session.commit()
        except:
            logg.exception("exception in ftree")
