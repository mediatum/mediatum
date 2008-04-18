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
import core.config as config
if os.getenv("MEDIATUM_CONFIG"):
    config.initialize(os.getenv("MEDIATUM_CONFIG"))
else:
    config.initialize("mediatum.cfg")

import utils.log
utils.log.initialize()
import logging
log = logging.getLogger('backend')

import sys
import os
import core.tree as tree
import core.acl as acl

log.info("Initializing backend...")

tree.initialize()

from contenttypes.directory import Directory
tree.registerNodeClass("directory", Directory)

# only for compatibility with older databases
tree.registerNodeClass("collection", Directory)
tree.registerNodeClass("collections", Directory)
tree.registerNodeClass("root", Directory)
tree.registerNodeClass("home", Directory)
tree.registerNodeClass("navitem", Directory)

from contenttypes.image import Image
tree.registerNodeClass("image", Image)
from contenttypes.document import Document
tree.registerNodeClass("document", Document)
from contenttypes.flash import Flash
tree.registerNodeClass("flash", Flash)
from contenttypes.video import Video
tree.registerNodeClass("video", Video)
from core.user import User
tree.registerNodeClass("user", User)
from core.usergroup import UserGroup
tree.registerNodeClass("usergroup", UserGroup)
from contenttypes.default import Default
tree.registerNodeClass("default", Default)

from schema.schema import Metadatatype, Metadatafield, Mask, Maskitem
tree.registerNodeClass("metadatatype", Metadatatype)
tree.registerNodeClass("metafield", Metadatafield)
tree.registerNodeClass("mask", Mask)
tree.registerNodeClass("maskitem", Maskitem)

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

# make all subnodes of collections collections
for n in tree.getRoot("collections").getChildren():
    if "directory" in n.type:
        print "making node",n.id,n.name,"a collection"
        n.setContentType("collection")
        n.setSchema(None)

for k,v in config.getsubset("plugins").items():
    print 'Initializing plugin "'+k+'"'
    path,module = splitpath(v)
    if path and path not in sys.path:
        sys.path += [path]
    m = __import__(module)

import search.query
search.query.startThread()
