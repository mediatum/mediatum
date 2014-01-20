#!/usr/bin/python
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

import os
import sys
import hashlib
import locale
import core.config as config

import core.athana as athana

#basedir = os.path.dirname(athana.__file__).rsplit(os.sep,1)[0]
# wn 2014-01-20: ensure absolute path even when importing startup file (eg: start.py)
# this won't change anything when starting via "python start.py"
basedir = os.path.abspath(athana.__file__).rsplit(os.sep,2)[0]

editmodulepaths = [('', 'web/edit/modules')]

print "Base path is at", basedir
print "Python Version is", sys.version.split("\n")[0]

if os.getenv("MEDIATUM_CONFIG"):
    config.initialize(basedir, os.getenv("MEDIATUM_CONFIG"))
else:
    config.initialize(basedir, "mediatum.cfg")

athana.setTempDir(config.settings["paths.tempdir"])
athana.setServiceUser(config.get("host.serviceuser",""))
athana.setServicePwd(hashlib.md5(config.get("host.servicepwd", "")).hexdigest())

# locale setting for sorting, default to system locale
loc = locale.setlocale(locale.LC_COLLATE, '')
print("using locale {} for sorting".format(loc))

import utils.log
utils.log.initialize()
import logging
log = logging.getLogger('backend')

import core.tree as tree
import core.acl as acl

log.info("Initializing backend...")

tree.initialize()

from contenttypes.directory import Directory
tree.registerNodeClass("directory", Directory)
from contenttypes.project import Project
tree.registerNodeClass("project", Project)

# only for compatibility with older databases
tree.registerNodeClass("collection", Directory)
tree.registerNodeClass("collections", Directory)
tree.registerNodeClass("root", Directory)
tree.registerNodeClass("home", Directory)


# register types in definition directory /contenttypes
log.info("Loading Content types")
for root, dirs, files in os.walk(os.path.join(config.basedir, 'contenttypes')):
    for name in [f for f in files if f.endswith(".py") and f!="__init__.py"]:
        m = __import__("contenttypes."+name[:-3])
        m = eval("m."+name[:-3]+"."+name[0].upper()+name[1:-3])
        tree.registerNodeClass(name[:-3], m)

from core.user import User
tree.registerNodeClass("user", User)
from core.usergroup import UserGroup
tree.registerNodeClass("usergroup", UserGroup)
from contenttypes.default import Default
tree.registerNodeClass("default", Default)

from core.shoppingbag import ShoppingBag
tree.registerNodeClass("shoppingbag", ShoppingBag)

from schema.schema import Metadatatype, Metadatafield, Mask, Maskitem
tree.registerNodeClass("metadatatype", Metadatatype)
tree.registerNodeClass("metafield", Metadatafield)
tree.registerNodeClass("mask", Mask)
tree.registerNodeClass("maskitem", Maskitem)
from schema.searchmask import SearchMaskItem
tree.registerNodeClass("searchmaskitem", SearchMaskItem)

import schema.schema as schema
tree.registerNodeFunction("getMetaFields", schema.node_getMetaFields)
tree.registerNodeFunction("getMetaField", schema.node_getMetaField)
tree.registerNodeFunction("getSearchFields", schema.node_getSearchFields)
tree.registerNodeFunction("getSortFields", schema.node_getSortFields)
tree.registerNodeFunction("getMasks", schema.node_getMasks)
tree.registerNodeFunction("getMask", schema.node_getMask)
tree.registerNodeFunction("getDescription", schema.node_getDescription)

from schema.mapping import Mapping, MappingField
tree.registerNodeClass("mapping", Mapping)
tree.registerNodeClass("mappingfield", MappingField)

from workflow import workflow
workflow.register()

from utils.utils import splitpath

#LDAP activated
if config.get("ldap.activate", "").lower()=="true":
    print "activate LDAP login"
    from core.userldap import LDAPUser
    import core.users as users
    users.registerAuthenticator(LDAPUser(), "ldapuser")

# load archive manager
archivemanager = None
try:
    import core.archive as archive
    archivemanager = archive.ArchiveManager()
except ImportError:
    print "error while initialization of archive manager"

# make all subnodes of collections collections
for n in tree.getRoot("collections").getChildren():
    if "directory" in n.type:
        n.setContentType("collection")
        n.setSchema(None)

if not tree.getRoot().hasChild("searchmasks"):
    tree.getRoot().addChild(tree.Node(name="searchmasks", type="searchmasks"))

for k,v in config.getsubset("plugins").items():
    print 'Initializing plugin "'+k+'"'
    path,module = splitpath(v)
    if path and path not in sys.path:
        sys.path += [path]
    m = __import__(module)

    if hasattr(m, 'pofiles'): # add po file paths
        if len(m.pofiles)>0:
            print "  load translation files"
            for fp in m.pofiles:
                translation.addPoFilepath([fp])

