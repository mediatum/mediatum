# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from warnings import warn
from core import db, Node, UserGroup


q = db.query


def loadGroupsFromDB():
    warn("use q(UserGroup).order_by(UserGroup.name)", DeprecationWarning)
    return q(UserGroup).order_by(UserGroup.name)


def getGroup(name_or_id):
    try:
        nid = long(name_or_id)
    except ValueError:
        warn("use q(UserGroup).filter_by(name=name)", DeprecationWarning)
        return q(UserGroup).filter_by(name=name_or_id).scalar()
    else:
        warn("use q(UserGroup).get(id)", DeprecationWarning)
        return q(UserGroup).get(nid)


def create_group(name, description="", option="", dynamic_users="", allow_dynamic=""):
    raise Exception("use UserGroup constructor")

""" get number of users containing given group """


def getNumUsers(grp):
    raise Exception("use q(UserGroup).count()")
    return len(getGroup(grp).getChildren())


def getMetadata(grp):
    """Get Metadatatypes which can be read by the given group"""
    raise Exception("obsolete")


def saveGroupMetadata(group, metaList):
    """Sets permitting access rules for given `group` on the metadatatypes in metaList.
    Metadatatypes not mentioned in metaList will have the access right removed for `group`"""
    raise Exception("obsolete")


def deleteGroup(grp):
    raise Exception("implement this...")


def existGroup(grp):
    raise Exception("use q(UserGroup).filter_by(name=name)")


def updateAclRule(oldname, newname):
    raise Exception("obsolete")


def sortUserGroups():
    raise Exception("use q(UserGroup).")
