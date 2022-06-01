# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

import core.translation as _core_translation
import web.edit.edit_common as _web_edit_edit_common
from core.users import getHomeDir
from core.users import user_from_session as _user_from_session
import logging
from contenttypes import Collections, Container
from core import Node
from core import db

logg = logging.getLogger(__name__)
q = db.query

def getInformation():
    return {"version":"1.1", "system":1}

def getContent(req, ids):
    logg.error("publish.getContent")
    user = _user_from_session()
    publishdir = q(Node).get(ids[0])
    ret = ""

    errorids = []
    publisherror = []
    changes = []
    if "dopublish" in req.params.keys():
        logg.debug("dopublish")
        num_req_err_nodes = 0
        num_db_err_nodes = 0
        num_rights_err_nodes = 0
        objlist = []
        for key in req.params.keys():
            if key.isdigit():
                objlist.append(key)
                src = q(Node).get(req.params.get("id"))

        for obj_id in objlist:
            remove_from_src = False
            obj = q(Node).get(obj_id)
            metadatatype = obj.metadatatype
            mask_validated = False
            for mask in metadatatype.getMasks(type="edit"): # check required fields
                if mask.has_read_access() and mask.getName() == obj.system_attrs.get("edit.lastmask"):
                    for f in mask.validateNodelist([obj]):
                        errorids.append(f)
                    mask_validated = True

            logg.error("%s", errorids)
            if len(errorids)>0: # object faulty
                num_req_err_nodes +=1
                # if object faulty, it is not necessary to do the rest of error handling for this object
                continue

            if not mask_validated:
                msg = "user %r going to publish node %r without having validated edit.lastmask" % (user, obj)
                logg.warning("%s", msg)
                # should we validate standard edit mask here?

            for dest_id in req.params.get("destination", "").split(","):
                if not dest_id: # no destination given
                    continue

                dest = q(Node).get(dest_id)

                # XXX: this error handling should be revised, I think...

                error = False # general rights error
                if not src.has_read_access():
                    logg.error("Error in publishing of node %r: source position %r has no read access.", obj.id, src.id)
                    error = True
                if not dest.has_write_access():
                    logg.error("Error in publishing of node %r: destination %r has no write access.", obj.id, dest.id)
                    error = True
                if not obj.has_write_access():
                    logg.error("Error in publishing of node %r: object has no write access.", obj.id)
                    error = True
                if not isinstance(dest, Container) or dest == src:
                    # cannot happen normally due to selection tree
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
                        num_rights_err_nodes += 1
                        errorids.append(obj.id)
                        logg.error(
                                "Error in publishing of node %s: Destination node %s is child of node.",
                                obj_id,
                                dest.id,
                            )
                else:
                    # error already logged
                    num_rights_err_nodes += 1
                    errorids.append(obj.id)

            if remove_from_src:
                try:
                    src.children.remove(obj)
                    db.session.commit()
                except:
                    num_db_err_nodes += 1
                    logg.exception("Error in publishing of node %s: Database error", obj.id)
                    errorids.append(obj.id)


        # error messages for publishing assistant
        if num_req_err_nodes > 0:
            if num_req_err_nodes < 2:
                publisherror.append(_core_translation.t(_core_translation.lang(req), "error_publish_single_node"))
            else:
                publisherror.append(_core_translation.t(_core_translation.lang(req), "error_publish_multiple_nodes"))
        if num_rights_err_nodes > 0:
            if num_rights_err_nodes < 2:
                publisherror.append(_core_translation.t(_core_translation.lang(req), "error_publish_rights_single"))
            else:
                publisherror.append(_core_translation.t(_core_translation.lang(req), "error_publish_rights_multiple"))
        if num_db_err_nodes > 0:
            if num_db_err_nodes < 2:
                publisherror.append(_core_translation.t(_core_translation.lang(req), "error_publish_database_single"))
            else:
                publisherror.append(_core_translation.t(_core_translation.lang(req), "error_publish_database_multiple"))

        v = {}
        v["id"] = publishdir.id
        v["change"] = changes
        ret += _tal.processTAL(v, file="web/edit/modules/publish.html", macro="reload", request=req)

    # build normal window
    stddir = ""  # preset value for destination ids
    stdname = ""
    show_dir_nav = _web_edit_edit_common.ShowDirNav(req, publishdir)
    ret += _tal.processTAL(
            dict(
                id=publishdir.id,
                stddir=stddir,
                stdname=stdname,
                showdir=show_dir_nav.showdir(publishwarn=None, markunpublished=1, faultyidlist=errorids),
                basedir=q(Collections).one(),
                script="var currentitem = '%s';\nvar currentfolder = '%s'" % (publishdir.id, publishdir.id),
                idstr=ids,
                faultyerrlist=publisherror,
                csrf=req.csrf_token.current_token,
            ),
            file="web/edit/modules/publish.html",
            macro="publish_form",
            request=req,
        )
    return ret
