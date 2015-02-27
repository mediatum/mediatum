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
import logging
from warnings import warn
from core.node import Node
from core import db
from core.usergroup import UserGroup
from utils.utils import Option


logg = logging.getLogger(__name__)
q = db.query

groupoption = []
groupoption += [Option("usergroup_option_1", "editor", "e", "img/edit_opt.png"),
                Option("usergroup_option_2", "workfloweditor", "w", "img/edit_opt.png")]

def loadGroupsFromDB():
    warn("use q(UserGroup).sort_by_name()", DeprecationWarning)
    return q(UserGroup).sort_by_name()


def getGroup(name_or_id):
    warn("use q(UserGroup).get(id) or q(UserGroup).filter_by(name=name)", DeprecationWarning)
    try:
        nid = long(name_or_id)
    except ValueError:
        warn("use q(UserGroup).filter_by(name=name)", DeprecationWarning)
        return q(UserGroup).filter_by(name=name_or_id).scalar()
    else:
        warn("use q(UserGroup).get(id)", DeprecationWarning)
        return q(UserGroup).get(nid)


def create_group(name, description="", option="", dynamic_users="", allow_dynamic=""):
    groups = tree.getRoot("usergroups")
    group = Node(name=name, type="usergroup")
    group.set("description",description)
    group.set("opts",option)
    if allow_dynamic:
        group.set("allow_dynamic", allow_dynamic)
    if dynamic_users:
        group.set("dynamic_users", dynamic_users)
    groups.addChild(group)
    logg.debug("created group %r (%r)", group.name, group.id)
    return group

""" get number of users containing given group """


def getNumUsers(grp):
    return len(getGroup(grp).getChildren())


def getMetadata(grp):
    results = []
    if grp.name == "":
        return results
    for mdt in tree.getRoot("metadatatypes").getChildren():
        acc = mdt.getAccess("read")
        if acc:
            if grp.name in acc.split(","):
                results.append(mdt.name)
    return results


def saveGroupMetadata(group, metaList):
    for meta in tree.getRoot("metadatatypes").getChildren():
        acc = meta.getAccess("read")
        if not acc:
            accList = []
        else:
            accList = acc.split(",")
        if meta.name in metaList:
            if group not in accList:
                if isinstance(accList, type([])):
                    if group != "":
                        accList.append(group)
                        accList = filter(None, accList)
                        meta.setAccess("read", ",".join(accList))
                else:
                    logg.error("Type error, no list: %s", type(accList))
        else:
            if group in accList:
                accList.remove(group)
                meta.setAccess("read", ",".join(accList))


""" delete given group """


def deleteGroup(grp):
    # remove users from group
    grp = getGroup(grp)
    logg.debug("going to remove group %r (%r)", grp.name, grp.id)
    children = grp.getChildren()
    logg.debug("going to remove %r children from group %r (%r)", len(children), grp.name, grp.id)
    for user in children:
        grp.removeChild(user)
    child_ids = [c.id for c in children]
    logg.debug("id's of %r children removed from group %r (%r): %r", len(children), grp.name, grp.id, child_ids)
    if grp.get("allow_dynamic") == "1":
        logg.debug("group %r (%r) allowed dynamic users. Attribute 'dynamic_users': %r", grp.name, grp.id, grp.get('dynamic_users'))
    # remove group from groups
    groups = tree.getRoot("usergroups")
    groups.removeChild(grp)
    logg.debug("removed group %r (%r) from %r (%r)", grp.name, grp.id, groups.name, groups.id)


def existGroup(grp):
    groups = tree.getRoot("usergroups")
    try:
        return groups.getChild(grp)
    except tree.NoSuchNodeError:
        return 0


def updateAclRule(oldname, newname):
    from core import acl
    newrule = acl.AccessRule(newname, "( group " + newname + " )", newname)
    if (acl.existRule(oldname)):
        acl.updateRule(newrule, oldname, newname, oldname)

    else:
        acl.addRule(newrule)


def sortUserGroups():
    groups = tree.getRoot("usergroups").getChildren().sort_by_fields("name")
    for g in groups:
        g.setOrderPos(groups.index(g))
