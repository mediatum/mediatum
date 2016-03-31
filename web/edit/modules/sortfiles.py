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

from sqlalchemy import func
from utils.utils import getCollection
from core.translation import t
from core.transition import httpstatus, current_user
from core import Node
from core import db
from schema.schema import Metadatatype

q = db.query


def getContent(req, ids):
    user = current_user
    node = q(Node).get(ids[0])

    if "sortfiles" in user.hidden_edit_functions or not node.has_write_access():
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    c = getCollection(node)

    if "globalsort" in req.params:
        c.set("sortfield", req.params["globalsort"])
    collection_sortfield = c.get("sortfield")
    db.session.commit()

    class SortChoice:

        def __init__(self, label, value):
            self.label = label
            self.value = value

    sortfields = [SortChoice(t(req, "off"), "")]
    schemas = (t[0] for t in c.all_children_by_query(q(Node.schema)
                                                  .filter_by(subnode=False)
                                                  .group_by(Node.schema)
                                                  .order_by(func.count(Node.schema).desc())))

    for schema in schemas:
        metadatatype = q(Metadatatype).filter_by(name=schema).one()
        if metadatatype:
            sort_fields = metadatatype.metafields.filter(Node.a.opts.like(u"%o%")).all()
            if sort_fields:
                for sortfield in sort_fields:
                    sortfields += [SortChoice(sortfield.getLabel(), sortfield.name)]
                    sortfields += [SortChoice(sortfield.getLabel() + t(req, "descending"), "-" + sortfield.name)]
                break


    return req.getTAL("web/edit/modules/sortfiles.html", {"node": node,
                                                          "collection_sortfield": collection_sortfield,
                                                          "sortchoices": sortfields,
                                                          "name": c.name},
                      macro="edit_sortfiles")
