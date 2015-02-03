# -*- coding: utf-8 -*-
'''
Created on 06.06.2013
@author: stenzel

mediatumipython
===============

mediaTUM command line based on many great IPython features and some extensions.

Run it
------

Command line, from the mediaTUM base directory::

    ipython -i bin/mediatumipython.py
    
    
In a IPython Notebook cell::

    %run bin/mediatumipython.py


Commands
--------

* `%l` - show current node info
* `%cd <node id>` - change to node
* `%child <child name>` - change to named child of current node


* `%sql` - run any sql statement (provided by ipython-sql)
* `%citeproc` - show citeproc mappings

You can omit the leading % most of the time.


SQLAlchemy
----------

The `q` function can be used to query the database. This returns SQLAlchemy model nodes, not mediaTUM nodes!

.. code-block:: python

    # count collections
    q(Node).filter_by(type="collection").count()
    
    # get a node named test, fails if none or more than one result found
    q(Node).filter_by(name="test").one()

    # get the first document
    q(Node).filter(Node.type.like("document/%").first()
    
    # get all metafields of Metadatatype #816859
    q(Node).get(816859).children.filter_by(type="metafield").all()
    
    # attribute access
    q(Node).get(816859)["description"]

SQL
---

See `ipython-sql documentation <https://pypi.python.org/pypi/ipython-sql>`_

.. code:: sql
    
    // select nodes with no parents
    %sql SELECT * FROM node where id NOT IN (SELECT cid FROM nodemapping)
    
    
Old mediaTUM
------------

You can use core.tree if you want to work with mediaTUM-defined nodes. `%init full` must be run to set up the database.

.. code:: python::

    nn = tree.getNode(816859)
    children = nn.getChildren()
    

Mixing SQLAlchemy and core.tree
-------------------------------

SQLAlchemy nodes can return the corresponding mediaTUM node::

.. code:: python::

    sqla_node = q(Node).first()
    mediatum_node = sqla_node.m
 
WARNING: Reading from both objects should be safe, but write accesses could cause serious problems! Don't do this...   

'''
from __future__ import division, absolute_import, print_function
import logging as logg
import sys

from sqlalchemy import create_engine
from sqlalchemy.sql import *
from sqlalchemy.orm import sessionmaker

from core.db.sqla_mysql_datamodel import *
from utils.compat import itervalues

from core import config
import core.init as initmodule
from functools import wraps


if len(sys.argv) == 2:
    db = sys.argv[1].lower()
    if db == "mysql":
        # insert your favorite database connection here...
        SQLALCHEMY_CONNECTION = "mysql://user:password@localhost/database"
else:
    _connection_tmpl = "mysql://{user}:{passwd}@{dbhost}:{dbport}/{database}"
    SQLALCHEMY_CONNECTION = _connection_tmpl.format(
        user=config.get("database.user", "mediatum"),
        passwd=config.get("database.passwd", ""),
        dbhost=config.get("database.dbhost", "localhost"),
        dbport=int(config.get("database.dbport", "3306")),
        database=config.get("database.db", "mediatum")
    )

print("DB connection is: " + SQLALCHEMY_CONNECTION)

rootlogg = logg.getLogger()
rootlogg.handlers = []

# logg.basicConfig(level=logg.INFO)
# logg.getLogger("sqlalchemy.engine").setLevel(logg.INFO)

engine = create_engine(SQLALCHEMY_CONNECTION)
DeclarativeBase.metadata.bind = engine
s = db_session = sessionmaker(bind=engine)()
conn = engine.connect()
q = s.query

global last_inserted_node
last_inserted_node_id = None
global cnode
root = cnode = q(Node).get(1)
global lastnode
lastnode = root

nodes = Node.__table__
nodefiles = NodeFile.__table__
nodeattributes = NodeAttribute.__table__
    
    
### some Node extensions:

def _node_m(self):
    return tree.getNode(self.id)

Node.m = property(_node_m)


def all_nodes():
    return q(Node).all()


highest_node_id_stmt = select([func.max(nodes.c.id)]).compile()

nid_bp = bindparam("nid", type_=Integer)

node_delete_stmt = nodes.delete().where(nodes.c.id > nid_bp).compile()
nodemapping_delete_stmt = t_nodemapping.delete().where(or_(t_nodemapping.c.nid > nid_bp, t_nodemapping.c.cid > nid_bp)).compile()
nodeattribute_delete_stmt = nodeattributes.delete().where(nodeattributes.c.nid > nid_bp).compile()
nodefile_delete_stmt = nodefiles.delete().where(nodefiles.c.nid > nid_bp).compile()

delete_node_stmts = [node_delete_stmt, nodemapping_delete_stmt, nodeattribute_delete_stmt, nodefile_delete_stmt]


def cut_above_node(nid):
    return [conn.execute(s, nid=nid).rowcount for s in delete_node_stmts]


def highest_node_id():
    return conn.execute(highest_node_id_stmt).scalar()


def cut_last():
    if last_inserted_node_id:
        cut_above_node(last_inserted_node_id)


def get_child_ids(nids):
    """Returns all children for all nodes in sequence `nids`
    """
    stmt = select([t_nodemapping.c.cid.distinct()]).where(t_nodemapping.c.nid.in_(nids))
    res = conn.execute(stmt)
    return [t[0] for t in res]


def subtree_ids(start_id):
    """Returns all ids belonging to a subtree starting from `start_id` as root.
    """
    update = [start_id]
    nodes = set(update)

    while 1:
        update = get_child_ids(update)
        if not update:
            return nodes
        logg.debug("before %s, new: %s", len(nodes), len(update))
        nodes.update(update)


def get_all_node_ids():
    """Returns all node ids.
    """
    all_ids = {t[0] for t in conn.execute(select([Node.id]))}
    return all_ids


def repair_localread():
    old_localread_values= {nid: localread for nid, localread in q(Node.id, Node.localread)}
    Node.__table__.update().values(localread="")
    updated_localread_count = 0
    for nid in get_all_node_ids():
        node = q(Node).get(nid)
        new_localread = node.m.getLocalRead()
        old_localread = old_localread_values[nid]
        if new_localread != old_localread:
            logg.debug(u"localread changed for Node %s: %s -> %s", nid, old_localread, new_localread)
            updated_localread_count += 1
    return updated_localread_count


def purge_nodemappings():
    """Deletes all nodemappings which refer to non-existent Nodes
    """
    existing_subselect = q(Node.id).subquery()
    stmt = t_nodemapping.delete().\
        where(
        or_(
              ~t_nodemapping.c.nid.in_(existing_subselect), 
              ~t_nodemapping.c.cid.in_(existing_subselect)))
    res = conn.execute(stmt)
    return res
    
    
def purge_nodefiles():
    """Deletes all nodefiles which refer to non-existent Nodes
    """
    existing_subselect = q(Node.id).subquery()
    stmt = NodeFile.__table__.delete().where(~NodeFile.nid.in_(existing_subselect))
    res = conn.execute(stmt)
    return res
    
    
def purge_nodes():
    """Deletes all nodes which are unreachable from the root Node.
    """
    reachable_ids = subtree_ids(1)
    all_ids = get_all_node_ids()
    unreachable_ids = all_ids - reachable_ids
    logg.info("all nodes: %s, reachable from root node: %s, unreachable from root node: %s", 
              len(all_ids), len(reachable_ids), len(unreachable_ids))
    res = conn.execute(Node.__table__.delete().where(Node.id.in_(unreachable_ids)))
    return res
    
    
def purge_metadatatypes():
    """Deletes all metadatatypes which are unused
    """
    used_mdts = [t[0] for t in conn.execute(select([func.substring_index(Node.type, '/', -1)]).distinct())]
    stmt = Node.__table__.delete().where(and_(Node.type == 'metadatatype', ~Node.name.in_(used_mdts)))
    res = conn.execute(stmt)
    return res


def purge_exportmappings():
    """Deletes all exportmappings which are not used by any mask
    """
    used_exportmappings = [t[0] for t in 
                              q(t_nodeattribute.c.value.distinct()).
                              join(Node).
                              filter(Node.type == 'mask').
                              filter(t_nodeattribute.c.name == 'exportmapping')] 
    
    
    res = conn.execute(Node.__table__.delete().where(and_(Node.type == 'mapping', 
                                                          ~Node.id.in_(used_exportmappings))))
    return res
    
    
def purge_nodeattributes():
    all_node_ids = select([Node.id])
    res = conn.execute(t_nodeattribute.delete().where(~t_nodeattribute.c.nid.in_(all_node_ids)))
    return res


### IPython magic

from IPython.core.magic import Magics, magics_class, line_magic
from IPython.core.magic_arguments import argument, magic_arguments,\
    parse_argstring, defaults

# functions can check if mediaTUM is initialized correctly and report an error if this is not the case

INIT_STATES = {
    "basic": 100, # initmodule.basic_init()
    "full": 200 # initmodule.full_init()
}

REV_INIT_STATES = {v: k for k, v in INIT_STATES.items()}

def needs_init(min_state):
    def _needs_init(f):
        @wraps(f)
        def _inner(self, *args, **kwargs):
            if self.check_init_state(min_state):
                return f(self, *args, **kwargs)
        return _inner
        
    return _needs_init
    

@magics_class
class MediatumMagics(Magics):

    def __init__(self, shell):
        super(MediatumMagics, self).__init__(shell)
        self.init_state = 0

    def check_init_state(self, min_state):
        if self.init_state < INIT_STATES[min_state]:
            print("mediaTUM is not initialized properly. You must run '%init {}' first."
                  .format(min_state))
            return False
        return True

    @magic_arguments()
    @argument("nid", nargs="?", default="")
    @line_magic
    def cd(self, line):
        """Changes to node with id `nid`"""
        global cnode, lastnode
        args = parse_argstring(self.cd, line)
        nid = args.nid
        if nid == "":
            cnode, lastnode = root, cnode

        elif nid == "-":
            cnode, lastnode = lastnode, cnode
        else:
            new_node = q(Node).get(nid)
            if new_node:
                cnode, lastnode = new_node, cnode
            else:
                print("node {} not found.".format(nid))

    @magic_arguments()
    @argument("name")
    @line_magic("child")
    @line_magic("ch")
    def child(self, line):
        global cnode, lastnode
        args = parse_argstring(self.child, line)
        name = args.name.strip("\"'")
        try:
            cnode, lastnode = filter(lambda c: c.name == name, cnode.children)[0], cnode
        except IndexError:
            print(u"Child {} not found!".format(args.name))

    @line_magic
    def l(self, line):
        print(cnode)
        section_names = ["Parents", "Subnodes", "Attributes", "Files"]
        section_lines = [
            [u"{} {}:  {}".format(n.id, n.name, n.type) for n in cnode.parents],
            [u"{} {}:  {}".format(n.id, n.name, n.type) for n in cnode.children],
            [u"{} = {}".format(a.name, a.value) for a in itervalues(cnode.attributes)],
            [u"{} {} {}".format(a.filename, a.type, a.mimetype) for a in cnode.files]
        ]

        for name, lines in zip(section_names, section_lines):
            print(u"\t" + name + ":")
            for line in lines:
                print(u"\t\t" + line)

    @needs_init("basic")
    @magic_arguments()
    @argument("nid")
    @line_magic
    def remove(self, line):
        args = parse_argstring(self.remove, line)
        child = tree.getNode(args.nid)
        if child is None:
            print("Node #{} not found!".format(args.nid))
            return
        cnode.m.removeChild(child)
        
    @needs_init("basic")
    @magic_arguments()
    @argument("nid")
    @line_magic
    def ln(self, line):
        args = parse_argstring(self.ln, line)
        new_child = tree.getNode(args.nid)
        cnode.m.addChild(new_child)
        
    @needs_init("basic")
    @magic_arguments()
    @argument("-f", "--fix", action="store_true")
    @argument("-a", "--all", action="store_true", help="check all masks of all metadatatypes")
    @defaults(fix=False)
    @line_magic
    def checkmask(self, line):
        args = parse_argstring(self.checkmask, line)
        import schema.schema as metadatatypes
        if args.all:
            for mdt in q(Node).filter_by(type="metadatatype"):
                print("=" * 80)
                print("checking metadatatype", mdt.name)
                for mask in mdt.children.filter_by(type="mask"):
                    print("-" * 80)
                    print("checking mask {} of mdt {}".format(mask.name, mdt.name))
                    metadatatypes.checkMask(mask.m, fix=args.fix, verbose=1, show_unused=1)
        else:
            metadatatypes.checkMask(cnode.m, fix=args.fix, verbose=1, show_unused=1)
        
    @needs_init("basic")
    @magic_arguments()
    @argument("oldmask")
    @argument("newmask")
    @line_magic
    def clonemask(self, line):
        args = parse_argstring(self.clonemask, line)
        import schema.schema as metadatatypes
        metadatatypes.cloneMask(cnode.m.getChild(args.oldmask), args.newmask)
        
    @needs_init("basic")
    @magic_arguments()
    @argument("nid")
    @line_magic
    def postprocess(self, line):
        args = parse_argstring(self.postprocess, line)
        if args.nid == "":
            treenode = tree.getNode(cnode.id)
        else:
            treenode = tree.getNode(args.nid)
        if hasattr(treenode, "event_metadata_changed"):
            treenode.event_metadata_changed()
            logg.info("called event_metadata_changed")
        if hasattr(treenode, "event_files_changed"):
            treenode.event_files_changed()
            logg.info("called event_files_changed")

    @needs_init("basic")
    @line_magic
    def citeproc(self, line):
        import schema.citeproc as citeproc
        citeproc.check_mappings()

    @magic_arguments()
    @argument("type", default="full", nargs="?", help="init type. Full initializes everything, basic only important stuff")
    @line_magic
    def init(self, line):
        args = parse_argstring(self.init, line)
        new_state = args.type
        if new_state == "basic":
            initmodule.basic_init()
            if not self.init_state:
                self.init_state = INIT_STATES[new_state]
        else:
            initmodule.full_init()
            self.init_state = INIT_STATES[new_state]

    @line_magic
    def delete_mappings_for_missing_nodes(self, line):
        existing_subselect = q(Node.id).subquery()
        stmt = t_nodemapping.delete().where(~t_nodemapping.c.nid.in_(existing_subselect))
        res = conn.execute(stmt)
        return res
    
    @line_magic
    def purge_nodes(self, line):
        res = purge_nodes()
        print(res.rowcount, "nodes deleted")
        
    @line_magic
    def purge_nodemappings(self, line):
        res = purge_nodemappings()
        print(res.rowcount, "nodemapping entries deleted")
        
    @line_magic
    def purge_nodefiles(self, line):
        res = purge_nodefiles()
        print(res.rowcount, "nodefiles deleted")
        
    @line_magic
    def purge_metadatatypes(self, line):
        res = purge_metadatatypes()
        print(res.rowcount, "metadatatypes deleted")
        
    @line_magic
    def purge_exportmappings(self, line):
        res = purge_exportmappings()
        print(res.rowcount, "exportmappings deleted")
        
    @line_magic
    def purge_nodeattributes(self, line):
        res = purge_nodeattributes()
        print(res.rowcount, "attributes deleted")
        
    @line_magic
    def delete_subtree(self, start_id):
        pass
    
    @line_magic
    def repair_localread(self, line):
        updated_localread_count = repair_localread()
        print(updated_localread_count, "localread values repaired")
    

ip = get_ipython()  # @UndefinedVariable


def current_prompt():
    name = cnode.name
    name = name if len(name) < 80 else name[:77] + "..."
    prompt = u"cnode: {} {} \"{}\"\n[\\#]: ".format(cnode.id, cnode.type, name)
    return prompt
 
def set_prompt(ip):
    ip.magic("config PromptManager.in_template = current_prompt()")
    
ip.set_hook("pre_prompt_hook", set_prompt)

def load_ipython_extension(ip):
    """Load the extension in IPython."""
    ip.register_magics(MediatumMagics)

load_ipython_extension(ip)

### mediaTUM

import core.tree as tree

from core.db.database import getConnection
get_db_connection = getConnection
del getConnection

ip.magic("autocall 1")

try:
    ip.magic("reload_ext sql")
    ip.magic("sql $SQLALCHEMY_CONNECTION")
except ImportError:
    print("SQL magic not found! You should install the IPython sql extension: pip install ipython-sql")
