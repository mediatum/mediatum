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
import core.tree
import core.acl

log.info("Initializing backend...")

#import tree_xml
#tree.setImplementation(tree_xml)
#import acl_xml
#acl.setImplementation(acl_xml)

import core.tree_db
tree.setImplementation(tree_db)
import core.acl_db
acl.setImplementation(acl_db)


#def initDatatypes():
#    datatypes = loadAllDatatypes()
#    for datatype in datatypes:
#        exec('from objtypes.' + datatype.getName() + ' import ' + datatype.getClassname())
#        exec('tree.registerNodeClass("' +datatype.getName()+ '", '+ datatype.getClassname()+')')

from objtypes.directory import Directory
tree.registerNodeClass("directory", Directory)

# only for compatibility with older databases
tree.registerNodeClass("root", Directory)
tree.registerNodeClass("collection", Directory)
tree.registerNodeClass("collections", Directory)
tree.registerNodeClass("home", Directory)
tree.registerNodeClass("navitem", Directory)

from objtypes.image import Image
tree.registerNodeClass("image", Image)
from objtypes.document import Document
tree.registerNodeClass("document", Document)
from objtypes.flash import Flash
tree.registerNodeClass("flash", Flash)
from objtypes.video import Video
tree.registerNodeClass("video", Video)
#from objtypes.person import Person
#tree.registerNodeClass("person", Person)
#from objtypes.yearbook import Yearbook
#tree.registerNodeClass("yearbook", Yearbook)
from objtypes.user import User
tree.registerNodeClass("user", User)
from objtypes.usergroup import UserGroup
tree.registerNodeClass("usergroup", UserGroup)
from objtypes.default import Default
tree.registerNodeClass("default", Default)
from objtypes.metadatatype import Metadatatype, Metadatafield, Mask, Maskitem
tree.registerNodeClass("metadatatype", Metadatatype)
tree.registerNodeClass("metafield", Metadatafield)
tree.registerNodeClass("mask", Mask)
tree.registerNodeClass("maskitem", Maskitem)

from objtypes import workflow
workflow.register()

for k,v in config.getsubset("plugins").items():
    print 'Initializing plugin "'+k+'"'
    m = __import__(v)

if "athana" in sys.argv[0].lower():
    print "Precaching occurences"
    tree.getRoot().getAllOccurences()

import search.query
search.query.startThread()
