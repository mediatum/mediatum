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
import codecs
sys.path += ["../", "."]

from core.init import full_init
full_init()

import core.tree as tree
import core.acl as acl
import re
import string
import core.xmlnode as xmlnode
import schema.schema as metadatatypes

rootaccess = acl.getRootAccess()

path = []
node = tree.getRoot()
lastnodes = []


def findNode(node, id):
    try:
        return tree.getNode(id)
    except KeyError:
        pass
    except tree.NoSuchNodeError:
        pass
    except ValueError:
        pass
    except TypeError:
        pass
    for c in node.getChildren().sort_by_orderpos():
        if c.name == id:
            return c
    return None


class Command:

    def __init__(self, f, args):
        self.f = f
        self.args = args


def show_node():
    global node
    print "%s %s (type=%s)" % (node.id, node.getName(), node.type)
    print "    Parents:"
    for c in node.getParents().sort_by_orderpos():
        print "        %s %s" % (c.id, c.getName())
    print "    Subnodes:"
    for c in node.getChildren().sort_by_orderpos():
        print "        %s %s" % (c.id, c.name)
    print "    Nodedata:"
    if node.type.find("/") > 0:
        print "        scheme: %s" % node.getSchema()
    else:
        print "        scheme: -no scheme-"
    print "        datatype: %s" % node.getContentType()
    print "    Metadata:"
    for k, v in node.items():
        if isinstance(v, type("")) and len(v) > 80:
            print "        %s=%s..." % (k, v[0:80])
        else:
            print "        %s=%s" % (k, v)
    print "    Files:"
    for f in node.getFiles():
        if f.getType() == "tile-0-0-0":
            print "        %s  %s  %s" % (f.getName(), f.getType(), f.getMimeType())
            print "        ..."
        elif f.getType().startswith("tile-"):
            pass
        else:
            print "        %s  %s  %s" % (f.retrieveFile(), f.getType(), f.getMimeType())
    print "    ACLs:"
    for a in ["read", "write", "data"]:
        print "        %s %s" % (a, node.getAccess(a))


def get_child(name):
    global node
    try:
        node = node.getChild(name)
    except tree.NoSuchNodeError:
        print "No such node"
    print "Node is now %s %s" % (node.id, node.getName())


def get_acl(type):
    global node
    print "Access '%s': %s" % (type, node.getAccess(s[4:]))


def remove_node(name):
    global node
    c = findNode(node, name)
    if c:
        node.removeChild(c)
        print "Node %s %s removed" % (c.id, c.getName())
    else:
        print "Couldn't find node %s" % name


def set(key, value):
    if key == "nodename":
        node.setName(value)
        return
    elif key == "objtype":
        node.setTypeName(value)
        return
    elif key.startswith("acl."):
        node.setAccess(key[4:], value)
        return
    elif key == "password" and node.getContentType() == "user":
        print "error: user password can not be changed by cmdline"
        return
    if value:
        node.set(key, value)
    else:
        node.removeAttribute(key)


def get(key):
    if key == "nodename":
        print node.getName(value)
        return
    elif key == "objtype":
        print "objtype: %s schema %s" % (node.getContentType(), node.getSchema())
        return
    elif key == "password" and node.getContentType() == "user":
        print "error: user password can not be read by cmdline"
        return
    elif key.startswith("acl."):
        print node.getAccess(key[4:])
        return
    print node.get(key)


def search(query):
    global node
    nodelist = tree.NodeList(node.search(query))
    print "%s matches" % len(nodelist)
    i = 0
    for n in nodelist:
        print "Node %s %s" % (n.id, n.getName())
        i += 1
        if i > 10:
            print "..."
            break


def searchsort(query, sortfield):
    global node
    nodelist = node.search(query).sort_by_fields(sortfield)
    print "%s matches" % len(nodelist)
    i = 0
    for n in nodelist:
        print "Node %s %s" % (n.id, n.getName())
        i += 1
        if i > 10:
            print "..."
            break


def searchids(query):
    global node
    nodelist = node.search(query)
    print "%s matches" % len(nodelist)
    print sorted([int(n.id) for n in nodelist])


def ln(nodeid):
    global node
    node.addChild(tree.getNode(nodeid))


def cd(id):
    global node, lastnodes
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
        print "Node is now %s %s" % (node.id, node.getName())
    else:
        print "Node %s not found" % id


def create(type, name):
    global node
    n = node.addChild(tree.Node(type=type, name=name))
    print "Node %s created: %s" % (name, n.id)


def searchfields():
    global node, rootaccess
    occurs = node.getAllOccurences(rootaccess)
    for mtype, num in occurs.items():
        print "%s (%s)" % (mtype.getName(), num)
        if num > 0:
            for field in mtype.getMetaFields():
                if field.Searchfield():
                    print "\t %s %s %s" % (field.getName(), field.getFieldtype(), field.getValueList())


def importfile(filename):
    global node
    child = xmlnode.readNodeXML(filename)
    if child:
        node.addChild(child)
    else:
        print "\tfile '%s' not found" % filename


def exportfile(filename):
    global node
    xmlnode.writeNodeXML(node, filename)


def dumptree(filename):
    def recurse_chapters(fi, node, numbers):
        s = []
        for a in numbers:
            s.append("%d." % a)
        print "%s %s" % ("".join(s)[:-1], node.getName())
        fi.write("%s %s\n" % ("".join(s)[:-1], node.getName()))
        num = 1
        for c in node.getContainerChildren().sort_by_orderpos():
            recurse_chapters(fi, c, numbers + [num])
            num += 1

    with codecs.open(filename, "wb", encoding='utf8') as fi:
        recurse_chapters(fi, node, [1])


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
    if hasattr(node, "event_metadata_changed"):
        node.event_metadata_changed()
    if hasattr(node, "event_files_changed"):
        node.event_files_changed()


def genmasks(masktype):
    if masktype not in ["nodebig", "nodesmall", "editmask"]:
        print "Unknown mask type %s" % masktype
        return
    for metatype in tree.getRoot("metadatatypes").getChildren().sort_by_orderpos():
        metadatatypes.generateMask(metatype, masktype, 0)


def checkmask():
    metadatatypes.checkMask(node, fix=0, verbose=1, show_unused=1)


def fixmask():
    metadatatypes.checkMask(node, fix=1, verbose=1)


def checkmasks():
    for metatype in tree.getRoot("metadatatypes").getChildren().sort_by_orderpos():
        for mask in metatype.getMasks():
            errornum = metadatatypes.checkMask(mask, fix=0, verbose=0)
            if errornum:
                print "Mask %s/%s %s %s has %s errors" % (metatype.name, mask.name, mask.name, mask.id, errornum)


def clonemask(oldmask, newmask):
    metadatatypes.cloneMask(node.getChild(oldmask), newmask)


def showlist():
    print "known commands:"
    for name, command in commands.items():
        print "\t- %s %s " % (name, " ".join(['<%s>' % a for a in command.args]))


def changescheme(collection_id, newschemename, write=0):
    """ changes all elements (except directories) to given metascheme """
    node = tree.getNode(collection_id)
    i = 0
    j = 0
    for n in node.getAllChildren():
        if n.type != "directory":
            if ustr(write) == "1":
                i += 1
                try:
                    print "\tchangig scheme for node %s from '%s' to '%s'..." % (
                        n.id, n.type, n.type[0:n.type.index("/") + 1] + newschemename)
                    n.type = n.type[0:n.type.index("/") + 1] + newschemename
                except:
                    j += 1
            else:
                i += 1
                print "\t node to change %s current scheme '%s'" % (n.id, n.type)
    print "  %s node(s) affected (%s errors)" % (i, j)


def reindex():
    global node
    from core.tree import searcher

    nodes = node.getAllChildren()
    print "reindex started for %s nodes" % len(nodes)
    searcher.reindex(nodelist=nodes)


def event(etype="meta"):
    if etype == "meta":
        node.event_metadata_changed()
    elif etype == "file":
        node.event_files_changed()


def bibtex():
    import schema.bibtex as bibtex
    bibtex.checkMappings()


def citeproc():
    import schema.citeproc as citeproc
    citeproc.check_mappings()


def quit():
    sys.exit(1)


def searchindex():
    global node
    from core.tree import searcher

    print "writing indexvalues of searchindex for node '%s' (id %s) in file 'searchindex.log'" % (node.name, node.id)

    with codecs.open("searchindex.log", "wb", encoding='utf8') as fi:
        fi.write("searchindex for node '%s' (id: %s)\n\n" % (node.name, node.id))
        fi.write("* FULLSEARCHMETA:\n\n")

        i = 0
        fullfields = ["id", "type", "schema", "value"]
        for line in searcher.db.execute("select * from fullsearchmeta where fullsearchmeta match ?", ["'id: %s'" % node.id]):
            for part in line:
                for p in part.split("| "):
                    if i < len(fullfields):
                        fi.write(fullfields[i] + ":\n")

                    fi.write("  %s\n" % p)
                    i += 1

        fi.write("\n\n* SEARCHMETA:\n\n")
        i = 0
        fields = ["id", "type", "schema", "date"]

        sfields = searcher.db.execute("select position, attrname from searchmeta_def where name='%s'" % node.getSchema(), [])
        for f in sorted(sfields, key=lambda x, y: cmp(int(x[0]), int(y[0]))):
            fields.append(f[1])

        for line in searcher.db.execute("select * from searchmeta where searchmeta match ?", ["'id:%s'" % node.id]):
            for part in line:
                if i < len(fields):
                    fi.write("%s:\n" % fields[i])
                    fi.write(" %s\n" % part)
                i += 1

        fi.write("\n\n* SEARCHMETA:\n\n")
        i = 0
        fields = ["id", "type", "schema", "date"]

        sfields = searcher.db.execute("select position, attrname from searchmeta_def where name='%s'" % node.getSchema(), [])
        sfields.sort(lambda x, y: cmp(int(x[0]), int(y[0])))
        for f in sfields:
            fields.append(f[1])

        for line in searcher.db.execute("select * from searchmeta where searchmeta match ?", ["'id:%s'" % node.id]):
            for part in line:
                if i < len(fields):
                    fi.write("%s:\n" % fields[i])
                    fi.write(" %s\n" % ustr(part))
                i += 1

        fi.write("\n\n* TEXTSEARCHMETA:\n\n")
        i = 0
        fields = ["id", "type", "schema", "text"]
        for line in searcher.db.execute("select * from textsearchmeta where textsearchmeta match ?", ["'id:%s'" % node.id]):
            for field in fields:
                fi.write("%s:\n" % fields[i])
                fi.write(" %s\n" % line[i])
                i += 1


commands = {
    "show": Command(show_node, []),
    "ls": Command(show_node, []),
    "set": Command(set, ["key", "value"]),
    "event": Command(event, ["etype"]),
    "get": Command(get, ["key"]),
    "child": Command(get_child, ["name"]),
    "acl": Command(get_acl, ["type"]),
    "rm": Command(remove_node, ["name"]),
    "bibtex": Command(bibtex, []),
    "citeproc": Command(citeproc, []),
    "search": Command(search, ["query"]),
    "searchids": Command(searchids, ["query"]),
    "searchsort": Command(searchsort, ["query", "sortfield"]),
    "cd": Command(cd, ["id"]),
    "create": Command(create, ["type", "name"]),
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
    "clonemask": Command(clonemask, ["oldmask", "newmask"]),
    "reindex": Command(reindex, []),
    "?": Command(showlist, []),
    "changescheme": Command(changescheme, ["collection_id", "newschemename", "write"]),
    "searchindex": Command(searchindex, [])
}
print "\n\nmediaTUM CommandLineInterface\n('?' for commandlist)"
while True:
    s = raw_input('>> ')
    if not s:
        continue
    space = s.find(" ")
    if space < 0:
        cmd = s
        rest = ""
    else:
        cmd = s[:space]
        rest = s[space + 1:].strip() + " "

    if cmd == "search":
        search(rest)
    elif cmd in commands:
        command = commands[cmd]
        pattern = re.compile(r'([^ "]+|"[^"]*"|\'[^\']*\')\s+' * len(command.args))
        p = pattern.match(rest)

        if not p or len(p.groups()) != len(command.args):
            print "Invalid arguments for command %s" % cmd
            print "Usage:\n%s %s" % (cmd, string.join(command.args, " "))
        else:
            hashtable = {}
            for (key, value) in zip(command.args, p.groups()):
                if value.startswith('"""') and value.endswith('"""'):
                    value = value[3:-3]
                elif value[0] == '"' and value[-1] == '"':
                    value = value[1:-1]
                elif value[0] == '\'' and value[-1] == '\'':
                    value = value[1:-1]
                hashtable[key] = value
            command.f(**hashtable)
    else:
        print "Unknown command: %s" % cmd
