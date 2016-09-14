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

from web.edit.edit_common import showdir
from core.users import getHomeDir
from core.transition import current_user
import logging
from contenttypes import Collections, Container
from core import Node
from core import db

logg = logging.getLogger(__name__)
q = db.query

def getInformation():
    return {"version":"1.1", "system":1}

def getContent(req, ids):
    user = current_user
    publishdir = q(Node).get(ids[0])
    ret = ""

    actionerror = []
    changes = []
    if "dopublish" in req.params.keys():

        objlist = []
        for key in req.params.keys():
            if key.isdigit():
                objlist.append(key)
                src = q(Node).get(req.params.get("id"))

        for obj_id in objlist:
            faultylist = []
            remove_from_src = False
            obj = q(Node).get(obj_id)
            metadatatype = obj.metadatatype
            mask_validated = False
            for mask in metadatatype.getMasks(type="edit"): # check required fields
                if mask.has_read_access() and mask.getName() == obj.system_attrs.get("edit.lastmask"):
                    for f in mask.validateNodelist([obj]):
                        faultylist.append(f)
                    mask_validated = True

            if len(faultylist)>0: # object faulty
                actionerror.append(obj_id)
                continue

            if not mask_validated:
                msg = "user %r going to publish node %r without having validated edit.lastmask" % (user, obj)
                logg.warning(msg)
                # should we validate standard edit mask here?

            for dest_id in req.params.get("destination", "").split(","):
                if not dest_id: # no destination given
                    continue

                dest = q(Node).get(dest_id)

                # XXX: this error handling should be revised, I think...

                error = False
                if not src.has_read_access():
                    logg.error("Error in publishing of node %r: source position %r has no read access.", obj.id, src.id)
                    error = True
                if not dest.has_write_access():
                    logg.error("Error in publishing of node %r: destination %r has no write access.", obj.id, dest.id)
                    error = True
                if not obj.has_write_access():
                    logg.error("Error in publishing of node %r: object has no write access.", obj.id)
                    error = True
                if not isinstance(dest, Container):
                    logg.error("Error in publishing of node %r: destination %r is not a directory.", obj.id, dest.id)
                    error = True
                if dest == src:
                    logg.error("Error in publishing of node %r: destination %r is not a directory.", obj.id, dest.id)
                    error = True

                if not error:
                    if not obj.is_descendant_of(dest):
                        dest.children.append(obj)
                        remove_from_src = True

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

            if remove_from_src:
                try:
                    src.children.remove(obj)
                    db.session.commit()
                except:
                    logg.exception("Error in publishing of node %s: Database error", obj.id)
                    actionerror.append(obj.id)
                    

        v = {}
        v["id"] = publishdir.id
        v["change"] = changes
        ret += req.getTAL("web/edit/modules/publish.html", v, macro="reload")

    # build normal window
    stddir = ""  # preset value for destination ids
    stdname = ""

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
