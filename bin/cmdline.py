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
sys.path += ["../", "."]

import core
import core.tree as tree
import re
import string
import core.xmlnode as xmlnode
import schema.schema as metadatatypes

path = []
node = tree.getRoot()
lastnodes = []

def findNode(node, id):
    try:
        node = tree.getNode(id)
        return node
    except KeyError:
        pass
    except tree.NoSuchNodeError:
        pass
    except ValueError:
        pass
    except TypeError:
        pass
    for c in node.getChildren().sort():
        if c.name == id:
            return c
    return None

class Command:
    def __init__(self, f, args):
        self.f = f
        self.args = args

def show_node():
    global node
    print node.id,node.name,"(type="+node.type+")"
    print "    Parents:"
    for c in node.getParents().sort():
        print "        ",c.id,c.name
    print "    Subnodes:"
    for c in node.getChildren().sort():
        print "        ",c.id,c.name
    print "    Nodedata:"
    if node.type.find("/")>0:
        print "        scheme:",node.type[node.type.index("/")+1:]
        print "        datatype:",node.type[:node.type.index("/")]
    else:
        print "        scheme: -no scheme-"
        print "        datatype:",node.type
    print "    Metadata:"
    for k,v in node.items():
        if len(v)>80:
            print "        ",k+"="+v[0:80]+"..."
        else:
            print "        ",k+"="+v
    print "    Files:"
    for f in node.getFiles():
        print "        ",f.getPath()," ",f.getType()," ",f.getMimeType()
    print "    ACLs:"
    for a in ["read","write","data"]:
        print "        ",a,node.getAccess(a)


def get_child(name):
    global node
    try:
        node = node.getChild(name)
    except tree.NoSuchNodeError,e:
        print "No such node"
    print "Node is now",node.id,node.name

def get_acl(type):
    global node
    print "Access '"+type+"':",node.getAccess(s[4:])

def remove_node(name):
    global node
    c = findNode(node, name)
    if c:
        node.removeChild(c)
        print "Node",c.id,c.name,"removed"
    else:
        print "Couldn't find node",name

def set(key,value):
    if key=="nodename":
        node.setName(value)
        return
    elif key=="objtype":
        node.setTypeName(value)
        return
    elif key.startswith("acl."):
        node.setAccess(key[4:],value)
        return
    if value:
        node.set(key,value)
    else:
        node.removeAttribute(key)

def get(key):
    if key=="nodename":
        print node.getName(value)
        return
    elif key=="objtype":
        print "objtype:",node.getContentType()+"schema:"+node.getSchema()
        return
    elif key.startswith("acl."):
        print node.getAccess(key[4:])
        return
    print node.get(key)

def search(query):
    global node
    nodelist = node.search(query)
    print len(nodelist),"matches"
    i = 0
    for n in nodelist:
        print "Node",n.id,n.name
        i = i + 1
        if i > 10:
            print "..."
            break

def searchsort(query,sortfield):
    global node
    nodelist = node.search(query).sort(sortfield)
    print len(nodelist),"matches"
    i = 0
    for n in nodelist:
        print "Node",n.id,n.name
        i = i + 1
        if i > 10:
            print "..."
            break

def searchids(query):
    global node
    nodelist = node.search(query)
    print len(nodelist),"matches"
    ids = []
    for n in nodelist:
        ids += [int(n.id)]
    ids.sort()
    print ids

def ln(nodeid):
    global node
    c = tree.getNode(nodeid)
    node.addChild(c)

def cd(id):
    global node,lastnodes
    newnode = findNode(node, id)
    if id == "..":
        try:
            node = lastnodes.pop()
        except IndexError:
            print "root node reached"
        return

    if newnode:
        lastnodes += [node]
        node = newnode
        print "Node is now",node.id,node.name
    else:
        print "Node",id,"not found"

def create(type,name):
    global node
    n = tree.Node(type=type,name=name)
    node.addChild(n)
    "print Node",name,"created:",n.id

def searchfields():
    global node
    occurs = node.getAllOccurences()
    searchfields = []
    for mtype,num in occurs.items():
        print mtype.getName(), "(%d)" % num
        if num>0:
            fields = mtype.getMetaFields()
            for field in fields:
                if field.Searchfield():
                    print "\t",field.getName(), field.getFieldtype(), field.getValueList()

def importfile(filename):
    global node
    child = xmlnode.readNodeXML(filename)
    node.addChild(child)
    
def exportfile(filename):
    global node
    xmlnode.writeNodeXML(node, filename)

def dumptree(filename):
    def recurse_chapters(fi, node, numbers):
        s = ""
        for a in numbers:
            s += ("%d." % a)
        print s,node.name
        fi.write(s + " " + node.name + "\n")
        num = 1
        for c in node.getChildren().sort():
            if c.type == "directory" or c.type == "collection" or c.type == "collections":
                recurse_chapters(fi, c, numbers + [num])
                num = num+1

    fi = open(filename, "wb")
    recurse_chapters(fi, node, [1])
    fi.close()

def purge(ptype):
    if (node.type == "workflow" or node.type.startswith("workflowstep-")) and ptype == "workflow":
        def recurse(node):
            for c in node.getChildren():
                if not c.type.startswith("workflow"):
                    node.removeChild(c)
                else:
                    recurse(c)
        recurse(node)
    else:
        print "Unknown purge type '%s' or inside the wrong node (%s)" % (ptype, node.type)
        return

def postprocess():
    if hasattr(node,"event_metadata_changed"):
        node.event_metadata_changed()
    if hasattr(node,"event_files_changed"):
        node.event_files_changed()

def genmasks(masktype):
    if masktype not in ["nodebig","nodesmall","editmask"]:
        print "Unknown mask type",masktype
        return
    for metatype in tree.getRoot("metadatatypes").getChildren().sort():
        metadatatypes.generateMask(metatype,masktype, 0)

def checkmask():
    metadatatypes.checkMask(node,fix=0,verbose=1,show_unused=1)

def fixmask():
    metadatatypes.checkMask(node,fix=1,verbose=1)

def checkmasks():
    for metatype in tree.getRoot("metadatatypes").getChildren().sort():
        for mask in metatype.getMasks():
            errornum = metadatatypes.checkMask(mask,fix=0,verbose=0)
            if errornum:
                print "Mask",metatype.name,"/",mask.name,mask.id,"has",errornum,"errors"

def clonemask(oldmask,newmask):
    mask = node.getChild(oldmask)
    metadatatypes.cloneMask(mask, newmask)

def showlist():
    print "known commands:"
    for name,command in commands.items():
        print "\t-", name, " ".join(['<'+a+'>' for a in command.args])

def changescheme(collection_id, newschemename, write=0):
    """ changes all elements (except directories) to given metascheme """
    node = tree.getNode(collection_id)
    i = 0
    j = 0
    for n in node.getAllChildren():
        if n.type!="directory":
            if str(write)=="1":
                i += 1
                try:
                    print "\tchangig scheme for node %s from '%s' to '%s'..." % (n.id, n.type, n.type[0:n.type.index("/")+1]+newschemename)
                    n.type = n.type[0:n.type.index("/")+1]+newschemename
                except:
                    j += 1
            else:
                i+=1
                print "\t node to change %s current scheme '%s'" % (n.id, n.type)
    print "  %s node(s) affected (%s errors)" % (i,j)
   
def event(etype="meta"):
    if etype=="meta":
        node.event_metadata_changed()
    elif etype=="file":
        node.event_files_changed()
    
def quit():
    sys.exit(1)

commands = {
 "show": Command(show_node, []),
 "ls": Command(show_node, []),
 "set": Command(set, ["key","value"]),
 "event": Command(event, ["etype"]),
 "get": Command(get, ["key"]),
 "child": Command(get_child, ["name"]),
 "acl": Command(get_acl, ["type"]),
 "rm": Command(remove_node, ["name"]),
 "search": Command(search, ["query"]),
 "searchids": Command(searchids, ["query"]),
 "searchsort": Command(searchsort, ["query","sortfield"]),
 "cd": Command(cd, ["id"]),
 "create": Command(create, ["type","name"]),
 "searchfields": Command(searchfields, []),
 "quit": Command(quit, []),
 "export": Command(exportfile, ["filename"]),
 "import": Command(importfile, ["filename"]),
 "ln": Command(ln, ["nodeid"]),
 "purge": Command(purge, ["ptype"]),
 "dumptree": Command(dumptree, ["filename"]),
 "genmasks": Command(genmasks, ["masktype"]),
 "postprocess": Command(postprocess, []),
 "checkmask": Command(checkmask, []),
 "checkmasks": Command(checkmasks, []),
 "fixmask": Command(fixmask, []),
 "clonemask": Command(clonemask, ["oldmask","newmask"]),
 "?":Command(showlist,[]),
 "changescheme":Command(changescheme,["collection_id", "newschemename", "write"])
};
print "\n\nmediaTUM CommandLineInterface\n('?' for commandlist)"
while 1:
    s = raw_input('>> ')
    if not s:
        continue
    space = s.find(" ")
    if space<0:
        cmd = s
        rest = ""
    else:
        cmd = s[:space]
        rest = s[space+1:].strip() + " "

    if cmd in commands:
        command = commands[cmd]
        pattern = re.compile(r'([^ "]+|"[^"]*"|\'[^\']*\')\s+'*len(command.args))
        p = pattern.match(rest)
        if not p or len(p.groups()) != len(command.args):
            print "Invalid arguments for command",cmd
            print "Usage:"
            print cmd,string.join(command.args, " ")
        else:
            hashtable = {}
            for (key,value) in zip(command.args,p.groups()):
                if value[0] == '"' and value[-1] == '"':
                    value = value[1:-1]
                elif value[0] == '\'' and value[-1] == '\'':
                    value = value[1:-1]
                hashtable[key] = value
            command.f(**hashtable)
    else:
        print "Unknown command:",cmd
            

