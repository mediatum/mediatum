"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Peter Heckl <heckl@ub.tum.de>

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
