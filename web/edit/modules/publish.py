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

import core.users as users

import web.edit

from core.acl import AccessData
from core.translation import t, lang
from web.edit.edit_common import showdir
from web.edit.edit import nodeIsChildOfNode
from utils.utils import isDirectory
from core.users import getHomeDir
import logging
from contenttypes import Collections, Directory
from core import Node
from core import db

logg = logging.getLogger(__name__)
q = db.query

def getInformation():
    return {"version":"1.1", "system":1}

def getContent(req, ids):
    user = users.getUserFromRequest(req)
    publishdir = q(Node).get(ids[0])
    explicit = q(Node).filter(Node.write_access == user.login_name).all()
    ret = ""

    actionerror = []
    changes = []
    if "dopublish" in req.params.keys():
        access = AccessData(req)

        objlist = []
        for key in req.params.keys():
            if key.isdigit():
                objlist.append(key)
                src = q(Node).get(req.params.get("id"))

        for obj_id in objlist:
            faultylist = []
            obj = q(Node).get(obj_id)
            for mask in obj.getMasks(type="edit"): # check required fields
                if access.hasReadAccess(mask) and mask.getName() == obj.get("edit.lastmask"):
                    for f in mask.validateNodelist([obj]):
                        faultylist.append(f)

            if len(faultylist)>0: # object faulty
                actionerror.append(obj_id)
                continue

            for dest_id in req.params.get("destination", "").split(","):
                if not dest_id: # no destination given
                    continue

                dest = q(Node).get(dest_id)

                # XXX: this error handling should be revised, I think...

                if not src.has_read_access():
                    logg.error("Error in publishing of node %r: source position %r has no read access.", obj.id, src.id)
                    error = True
                if not dest.has_write_access():
                    logg.error("Error in publishing of node %r: destination %r has no write access.", obj.id, dest.id)
                    error = True
                if not obj.has_write_access():
                    logg.error("Error in publishing of node %r: object has no write access.", obj.id)
                    error = True
                if not isinstance(dest, Directory):
                    logg.error("Error in publishing of node %r: destination %r is not a directory.", obj.id, dest.id)
                    error = True
                if dest == src:
                    logg.error("Error in publishing of node %r: destination %r is not a directory.", obj.id, dest.id)
                    error = True

                if not error:
                    if not nodeIsChildOfNode(dest,obj):
                        dest.children.append(obj)
                        src.children.remove(obj)
                        db.session.commit()

                        if dest.id not in changes:
                            changes.append(dest.id)
                        if src.id not in changes:
                            changes.append(src.id)
                        logg.info("%s published %s (%s, %s) from src %s (%s, %s) to dest %s (%s, %s)", user.login_name,
                                  obj.id, obj.name, obj.type,
                                  src.id, src.name, src.type,
                                  dest.id, dest.name, dest.type)
                    else:
                        actionerror.append(obj.id)
                        logg.error("Error in publishing of node %s: Destination node %s is child of node.", obj_id, dest.id)

        v = {}
        v["id"] = publishdir.id
        v["change"] = changes
        ret += req.getTAL("web/edit/modules/publish.html", v, macro="reload")

    # build normal window
    stddir = ""
    stdname = ""
    l = []
    for n in explicit:
        if unicode(getHomeDir(user).id) != unicode(n):
            l.append(n)

    if len(l)==1:
        stddir = unicode(l[0])+","
        stdname = "- " + q(Node).get(l[0]).getName()

    v = {"id": publishdir.id,
         "stddir": stddir,
         "stdname": stdname,
         "showdir": showdir(req,
                            publishdir,
                            publishwarn=None,
                            markunpublished=1),
         "basedir": q(Collections).one(),
         "script": "var currentitem = '%s';\nvar currentfolder = '%s'" % (publishdir.id, publishdir.id), "idstr": ids,
         "faultylist": actionerror}

    ret += req.getTAL("web/edit/modules/publish.html", v, macro="publish_form")
    return ret
