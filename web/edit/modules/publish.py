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


logg = logging.getLogger(__name__)


def getInformation():
    return {"version":"1.1", "system":1}

def getContent(req, ids):
    user = users.getUserFromRequest(req)
    publishdir = tree.getNode(ids[0])
    explicit = tree.getNodesByAttribute("writeaccess", user.getName())
    ret = ""

    actionerror = []
    changes = []
    if "dopublish" in req.params.keys():
        access = AccessData(req)

        objlist = []
        for key in req.params.keys():
            if key.isdigit():
                objlist.append(key)
                src = tree.getNode(req.params.get("id"))

        for obj_id in objlist:
            faultylist = []
            obj = tree.getNode(obj_id)
            for mask in obj.getType().getMasks(type="edit"): # check required fields
                if access.hasReadAccess(mask) and mask.getName()==obj.get("edit.lastmask"):
                    for f in mask.validateNodelist([obj]):
                        faultylist.append(f)

            if len(faultylist)>0: # object faulty
                actionerror.append(obj_id)
                continue

            for dest_id in req.params.get("destination", "").split(","):
                if dest_id=="": # no destination given
                    continue

                dest = tree.getNode(dest_id)
                if dest != src and access.hasReadAccess(src) and access.hasWriteAccess(dest) and access.hasWriteAccess(obj) and isDirectory(dest):
                        if not nodeIsChildOfNode(dest,obj):
                            dest.addChild(obj)
                            src.removeChild(obj)

                            if dest.id not in changes:
                                changes.append(dest.id)
                            if src.id not in changes:
                                changes.append(src.id)
                            logg.info("%s published %s (%s, %s) from src %s (%s, %s) to dest %s (%s, %s)", user.name,
                                      obj.id, obj.name, obj.type,
                                      src.id, src.name, src.type,
                                      dest.id, dest.name, dest.type)
                        else:
                            actionerror.append(obj.id)
                            logg.error("Error in publishing of node %s: Destination node %s is child of node.", obj_id, dest.id)

                if not access.hasReadAccess(src):
                    logg.error("Error in publishing of node %r: source position %r has no read access.", obj.id, src.id)
                if not access.hasWriteAccess(dest):
                    logg.error("Error in publishing of node %r: destination %r has no write access.", obj.id, dest.id)
                if not access.hasWriteAccess(obj):
                    logg.error("Error in publishing of node %r: object has no write access.", obj.id)
                if not isDirectory(dest):
                    logg.error("Error in publishing of node %r: destination %r is not a directory.", obj.id, dest.id)

        v = {}
        v["id"] = publishdir.id
        v["change"] = changes
        ret += req.getTAL("web/edit/modules/publish.html", v, macro="reload")

    # build normal window
    stddir = ""
    stdname = ""
    l = []
    for n in explicit:
        if ustr(getHomeDir(user).id)!=ustr(n):
            l.append(n)

    if len(l)==1:
        stddir = ustr(l[0])+","
        stdname = "- " + tree.getNode(l[0]).getName()

    #v = {"id":publishdir.id,"stddir":stddir, "stdname":stdname, "showdir":showdir(req, publishdir, publishwarn=0, markunpublished=1, nodes=[])}
    v = {"id":publishdir.id,"stddir":stddir, "stdname":stdname, "showdir":showdir(req, publishdir, publishwarn=None, markunpublished=1, nodes=[])}
    v["basedir"] = tree.getRoot('collections')
    v["script"] = "var currentitem = '%s';\nvar currentfolder = '%s'" %(publishdir.id, publishdir.id)
    v["idstr"] = ids
    v["faultylist"] = actionerror
    ret += req.getTAL("web/edit/modules/publish.html", v, macro="publish_form")
    return ret
