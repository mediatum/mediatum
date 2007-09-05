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
import sys
sys.path += ["."]
import startup
import logging
from utils import *
import config
import os
from db import database

db = database.getConnection()

write=0

rootid = None
used_ids={}
nodemap={}

# ------- NODES -------

print "Checking",db.runQuery("select count(*) from node")[0][0],"nodes"

res = db.runQuery("select id,name,type from node")
for id,name,type in res:
    used_ids[id] = None
    nodemap[id] = []
    if type == "root":
        if rootid:
            print "More than one root id: ",rootid,id
            sys.exit(1)
        rootid = id

if not rootid:
    print "No root id"
    sys.exit(1)

# ------- NODEMAPPINGS -------

invalid_mappings = []

print "Checking",db.runQuery("select count(*) from nodemapping")[0][0],"nodemappings"

res = db.runQuery("select nid,cid from nodemapping")
for nid,cid in res:
    if nid not in used_ids or cid not in used_ids:
        invalid_mappings += [(nid,cid)]
    if nid in nodemap:
        nodemap[nid] += [cid]

if len(invalid_mappings):
    print "* Clearing",len(invalid_mappings),"invalid nodemappings"
    if write:
        for nid,cid in invalid_mappings:
            db.runQuery("delete from nodemapping where nid="+str(nid)+" and cid="+str(cid))

def mark(id,level=0):
    if(level==512):
        print "Recursion depth exceeded: Loop?"
        sys.exit(1)
    used_ids[id] = 1
    for cid in nodemap[id]:
        mark(cid,level+1)
mark(rootid)

unused = 0
for id,used in used_ids.items():
    if not used:
        unused = unused + 1

if unused:
    print "* Clearing",unused,"unused nodes"
    if write:
        for id,used in used_ids.items():
            if not used:
                db.runQuery("delete from node where id="+str(id))
                db.runQuery("delete from nodemapping where nid="+str(id))
    else:
        for id,used in used_ids.items():
            if not used:
                print id
del invalid_mappings
del nodemap

# ------- NODEATTRIBUTES -------

print "Checking",db.runQuery("select count(*) from nodeattribute")[0][0],"nodeattributes"

unused_attributes={}
res = db.runQuery("select nid,name,value from nodeattribute")
num_attribs = 0
for nid,name,value in res:
    if nid not in used_ids or not used_ids[nid]:
        unused_attributes[nid] = None
        num_attribs = num_attribs + 1
if num_attribs:
    print "* Clearing",num_attribs,"unused attributes"
    if write:
        for id in unused_attributes.keys():
            db.runQuery("delete from nodeattribute where nid="+str(id))
del unused_attributes

# ------- NODEFILES -------

print "Checking",db.runQuery("select count(*) from nodefile")[0][0],"nodefiles"

unused_files={}
used_files={}
res = db.runQuery("select nid,filename from nodefile")
num_files = 0
for nid,filename in res:
    if nid not in used_ids or not used_ids[nid]:
        unused_files[nid] = None
        num_files = num_files + 1
        if filename not in used_files:
            used_files[filename] = None
    else:
        used_files[filename] = 1
if num_files:
    print "* Clearing",num_files,"unused files"
    if write:
        for id in unused_files.keys():
            db.runQuery("delete from nodefile where nid="+str(id))
files_to_delete=0
for filename,used in used_files.items():
    if not used:
        files_to_delete=files_to_delete+1
if files_to_delete:
    print "* Deleting",files_to_delete,"unused files from disc"
    if write:
        for filename,used in used_files.items():
            if not used:
                print filename
                # TODO

prefix = config.get("paths.datadir")
orphan_files = {}
def recursedir(path):
    for file in os.listdir(os.path.join(prefix,path)):
        f = os.path.join(path,file)
        if os.path.isdir(os.path.join(prefix,f)):
            recursedir(f)
        else:
            if f in used_files and used_files[f]:
                pass
            else:
                orphan_files[f] = None
                #print f,len(used_files)
                #break
                #os.system("ls -l "+os.path.join(prefix,f))

recursedir("incoming")

del unused_files
del used_files

