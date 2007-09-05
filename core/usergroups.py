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
#
# needs sql table usergroup:
#   - name varchar(50) (primary key, index, unique, not null)
#   - description text
#

import core.config as config
from utils.utils import Option
import tree
import acl

groupoption = []
groupoption += [Option("usergroup_option_1", "editor", "e", "img/edit_opt.png"), 
                Option("usergroup_option_2", "workfloweditor", "w", "img/edit_opt.png")]

""" load all groups from db """
def loadGroupsFromDB():
    groups = tree.getRoot("usergroups")
    return groups.getChildren()

""" get group from db """
def getGroup(id):
    groups = tree.getRoot("usergroups")
    return groups.getChild(id)

""" create new group in db """
def create_group(name,description="",option=""):
    groups = tree.getRoot("usergroups")
    group = tree.Node(name=name, type="usergroup")
    group.set("description",description)
    group.set("opts",option)
    groups.addChild(group)
    return group
    
""" get number of users containing given group """
def getNumUsers(grp):
    return len(getGroup(grp).getChildren())

""" delete given group """
def deleteGroup(grp):
    # remove users from group
    grp = getGroup(grp)
    for user in grp.getChildren():
        grp.removeChild(user)
    # remove group from groups
    groups = tree.getRoot("usergroups")
    groups.removeChild(grp)

def existGroup(grp):
    groups = tree.getRoot("usergroups")
    try:
        return groups.getChild(grp)
    except tree.NoSuchNodeError:
        return 0

def createAcRule(name):
    acl.addRule(acl.AccessRule(name, "( group "+name+" )", name))
    

