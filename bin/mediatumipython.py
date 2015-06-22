# -*- coding: utf-8 -*-
'''
Created on 06.06.2013
@author: stenzel

***************
mediatumipython
***************

mediaTUM command line based on many great IPython features and some extensions.

Run it
======

Command line, from the mediaTUM base directory::

    ipython -i bin/mediatumipython.py


In a IPython Notebook cell::

    %run bin/mediatumipython.py


Basics
======

* shell-like "filesystem" browsing for the mediaTUM node tree
* IPython prompt shows the current node
* the current node can be accessed with `cnode`, the previous node with `lastnode`


Commands
========

Commands are implemented as IPython magic functions. You can omit the leading % most of the time.

Initialization
--------------

* `%init full` - init everything, needed for some commands.
    At startup, only important stuff is initialized (database, plugins, ...) automatically.


Change current node
-------------------

* `%cd <nid>` - change current node by ID
* `%cd -` - change to previous node
* `%child <child name>` - change to named child of current node (alias ch)


Display info for current node
-----------------------------

* `%list_all` - list current node info for all categories: parents, children, attributes, files (alias l)
* `%list_attributes` - (alias la)
* `%list_children` - (alias lc)
* `%list_parents` - (alias lp)
* `%list_files` - (alias lf)


Set `limit_number_of_info_lines = <n>` to display only the first <n> lines of a category.


Change the tree
---------------

* `%link <nid>` - add node with <nid> as child to current node
* `%remove <nid>` - remove child with <nid> from current node


SQL shortcuts
-------------

See `ipython-sql documentation <https://pypi.python.org/pypi/ipython-sql>`_ for more info.

* `%sql` - run any sql statement (provided by ipython-sql)
* `%select` - run a select statement
* `%insert` - run a insert statement
* `%update` - run a update statement
* `%delete` - run a delete statement


Misc information
----------------

* `%citeproc` - show citeproc mappings


Maintenance
^^^^^^^^^^^

* `%postprocess <nid>` - run postprocessing on current node or <nid>, if given
* `%checkmask [--fix] [--all] [--allmasks]` - run integrity checks on masks, see %checkmask? for details
* `%purge_nodes`: delete nodes that are not connected to the root node in any way ("unreachable nodes")


SQLAlchemy
==========

The `q` function can be used to query the database:


Node queries
------------

.. code-block:: python

    # count collections
    q(Collection).count()

    # get a node named test, fails if none or more than one result found
    q(Data).filter_by(name="test").one()

    # get a node named test, fails if more than one result found, returns None if none found
    q(Data).filter_by(name="test").scalar()

    # get the first document
    q(Document).first()

    # get all content children of Collection #993321
    q(Collection).get(993321).content_children # returns NodeAppenderQuery
    q(Collection).get(993321).content_children.all() # returns list

    # get all masks of Metadatatype #816859
    q(Metadatatype).get(816859).masks.all()

    # attribute access
    q(Data).get(816859)["description"]
    q(Data).get(816859).a.description

'''
from __future__ import division, absolute_import, print_function
import logging
import sys

from sqlalchemy import sql, text
from sqlalchemy.orm.exc import NoResultFound

from core.database.postgres import *
from utils.compat import *

from core import config
import core.init as initmodule
from functools import wraps

from core import init
import core.database
from core.database.postgres.node import t_noderelation
from itertools import islice
from collections import OrderedDict
init.basic_init()
# we don't want to raise exceptions for missing node classes
init.check_undefined_nodeclasses()

from core import Node, File

q = core.db.query
s = core.db.session

# settings

# set this to INFO for SQL statement echo, DEBUG for even more info from SQLAlchemy
SQLALCHEMY_LOGGING = logging.WARN

# use default connection specified by mediatum config for ipython-sql
SQLALCHEMY_CONNECTION = core.db.connectstr
# TODO: changing the connection string should be possible for the postgres connector, too

# load types for interactive querying
from contenttypes import Audio, Content, Directory, Collection, Container, Collections, Home, Document, Flash, Image, Imagestream, \
    Project, Video, Data
from core.systemtypes import Mappings, Metadatatypes, Root, Navigation, Searchmasks
from schema.schema import Metadatatype, Maskitem, Mask, Metafield
from workflow.workflow import Workflow, Workflows

from sqlalchemy.exc import SQLAlchemyError

# disable mediatum loggers
rootlogg = logging.getLogger()
rootlogg.handlers = []

# init stdout logging
logging.basicConfig(level=logging.INFO)

logging.getLogger("sqlalchemy.engine").setLevel(SQLALCHEMY_LOGGING)

global last_inserted_node
last_inserted_node_id = None
global cnode
# root can be None for uninitialized / corrupt databases. We allow this.
root = cnode = q(Root).scalar()
global lastnode
lastnode = root

global limit_number_of_info_lines
limit_number_of_info_lines = None

# IPython magic

from IPython.core.magic import Magics, magics_class, line_magic, needs_local_scope
from IPython.core.magic_arguments import argument, magic_arguments,\
    parse_argstring, defaults

# functions can check if mediaTUM is initialized correctly and report an error if this is not the case

INIT_STATES = {
    "basic": 100,  # initmodule.basic_init() default
    "full": 200  # initmodule.full_init()
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


def reachable_node_ids():
    return q(t_noderelation.c.cid).filter(t_noderelation.c.nid == 1).union_all(sql.select([sql.expression.literal(1)]))


def delete_unreachable_nodes(synchronize_session='fetch'):
    reachable_nodes_sq = reachable_node_ids().subquery()
    s.execute(t_noderelation.delete(~t_noderelation.c.nid.in_(reachable_nodes_sq)))
    s.execute(t_noderelation.delete(~t_noderelation.c.cid.in_(reachable_nodes_sq)))
    q(File).filter(~File.nid.in_(reachable_nodes_sq)).delete(synchronize_session)
    return q(Node).filter(~Node.id.in_(reachable_nodes_sq)).delete(synchronize_session)


def unreachable_nodes():
    reachable_node_sq = reachable_node_ids().subquery()
    return q(Node).filter(~Node.id.in_(reachable_node_sq))


INFO_PRODUCERS = OrderedDict([
    ("parents", lambda node: (u"{} {}:  {}".format(n.id, n.name, n.type) for n in node.parents)),
    ("children", lambda node: (u"{} {}:  {}".format(n.id, n.name, n.type) for n in node.children)),
    ("attributes", lambda node: (u"{} = {}".format(name, value) for name, value in iteritems(node.attrs))),
    ("files", lambda node: (u"{} {} {}".format(a.path, a.filetype, a.mimetype) for a in node.files))]
)


def print_info_for_category(category, limit=None):
    if limit is None:
        limit = limit_number_of_info_lines

    print(u"\t" + category.capitalize() + ":")
    info_producer = INFO_PRODUCERS[category]

    for line in islice(info_producer(cnode), 0, limit):
        print(u"\t\t" + line)


@magics_class
class MediatumMagics(Magics):

    def __init__(self, shell):
        super(MediatumMagics, self).__init__(shell)
        self.init_state = INIT_STATES["basic"]

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
                print(u"node {} not found.".format(nid))

    @magic_arguments()
    @argument("name")
    @line_magic("child")
    @line_magic("ch")
    def child(self, line):
        global cnode, lastnode
        args = parse_argstring(self.child, line)
        name = args.name.strip("\"'")
        try:
            cnode, lastnode = cnode.children.filter_by(name=name).one(), cnode
        except NoResultFound:
            print(u"Child {} not found!".format(args.name))

    @line_magic("list_all")
    @line_magic("l")
    def list_all(self, line):
        print(cnode)
        for category in INFO_PRODUCERS:
            print_info_for_category(category)

    @line_magic("list_attributes")
    @line_magic("la")
    def list_attributes(self, line):
        print_info_for_category("attributes")

    @line_magic("list_children")
    @line_magic("lc")
    def list_children(self, line):
        print_info_for_category("children")

    @line_magic("list_parents")
    @line_magic("lp")
    def list_parents(self, line):
        print_info_for_category("parents")

    @line_magic("list_files")
    @line_magic("lf")
    def list_files(self, line):
        print_info_for_category("files")

    @needs_init("basic")
    @magic_arguments()
    @argument("nid")
    @line_magic
    def remove(self, line):
        args = parse_argstring(self.remove, line)
        try:
            child = cnode.children.filter_by(id=long(args.nid)).one()
        except NoResultFound:
            print(u"Child {} not found!".format(args.nid))
            return
        cnode.children.remove(child)

    @needs_init("basic")
    @magic_arguments()
    @argument("nid")
    @line_magic("link")
    @line_magic("ln")
    def ln(self, line):
        args = parse_argstring(self.ln, line)
        new_child = q(Node).get(args.nid)
        cnode.children.append(new_child)

    @needs_init("basic")
    @magic_arguments()
    @argument("-f", "--fix", action="store_true")
    @argument("-a", "--all", action="store_true", help="check all masks of current metadatatypes")
    @argument("-m", "--allmasks", action="store_true", help="check all masks of *all* metadatatypes")
    @defaults(fix=False)
    @line_magic
    def checkmask(self, line):
        args = parse_argstring(self.checkmask, line)
        import schema.schema as metadatatypes
        if args.all:
            def check_masks_of_mdt(mdt):
                for mask in mdt.masks:
                    print("-" * 80)
                    print(u"checking mask {} of mdt {}".format(mask.name, mdt.name))
                    metadatatypes.checkMask(mask, fix=args.fix, verbose=1, show_unused=1)

            if args.allmasks:
                for mdt in q(Metadatatype):
                    print("=" * 80)
                    print("checking metadatatype", mdt.name)
                    check_masks_of_mdt(mdt)
            else:
                check_masks_of_mdt(cnode)
        else:
            metadatatypes.checkMask(cnode, fix=args.fix, verbose=1, show_unused=1)

    @needs_init("basic")
    @magic_arguments()
    @argument("oldmask")
    @argument("newmask")
    @line_magic
    def clonemask(self, line):
        raise NotImplementedError("not yet implemented in mediaTUM postgres")
        args = parse_argstring(self.clonemask, line)
        import schema.schema as metadatatypes
        metadatatypes.cloneMask(cnode.children.filter_by(name=args.oldmask), args.newmask)

    @needs_init("basic")
    @magic_arguments()
    @argument("nid", default=None)
    @line_magic
    def postprocess(self, line):
        args = parse_argstring(self.postprocess, line)
        if not args.nid:
            node = cnode
        else:
            node = q(Node).get(args.nid)
        if hasattr(node, "event_metadata_changed"):
            node.event_metadata_changed()
            logg.info("called event_metadata_changed")
        if hasattr(node, "event_files_changed"):
            node.event_files_changed()
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
    def purge_nodes(self, line):
        res = delete_unreachable_nodes(synchronize_session=False)
        s.expire_all()
        print(res, "nodes deleted")


ip = get_ipython()  # @UndefinedVariable


def current_prompt():
    if cnode:
        name = cnode.name
        name = name if len(name) < 80 else name[:77] + "..."
        prompt = u"cnode: {} {} \"{}\"\n[\\#]: ".format(cnode.id, cnode.type, name)
    else:
        prompt = "no cnode [\\#] "
    return prompt


def set_prompt(ip):
    ip.magic("config PromptManager.in_template = current_prompt()")

ip.set_hook("pre_prompt_hook", set_prompt)

# setup custom exception handler for automatic rollbacks on SQLAlchemy errors


def handle_sqla_exception(self, etype, value, tb, tb_offset=None):
    from core import db
    db.session.rollback()
    self.showtraceback((etype, value, tb), tb_offset=0)
    stb = self.InteractiveTB.structured_traceback(
        (etype, value, tb), tb_offset=tb_offset)
    return stb

ip.set_custom_exc((SQLAlchemyError,), handle_sqla_exception)

try:
    from sql.magic import SqlMagic
except ImportError:
    print("SQL magic not found! You should install the IPython sql extension: pip install ipython-sql")
    SQLMagics = None
else:
    @magics_class
    class SQLMagics(SqlMagic):

        """Some additions to ipython-sql, could be merged"""

        @needs_local_scope
        @line_magic("select")
        def select(self, line, cell='', local_ns={}):
            return self.execute("SELECT " + line, cell, local_ns)

        @needs_local_scope
        @line_magic("delete")
        def delete(self, line, cell='', local_ns={}):
            return self.execute("DELETE " + line, cell, local_ns)

        @needs_local_scope
        @line_magic("insert")
        def insert(self, line, cell='', local_ns={}):
            return self.execute("INSERT " + line, cell, local_ns)

        @needs_local_scope
        @line_magic("update")
        def update(self, line, cell='', local_ns={}):
            return self.execute("UPDATE " + line, cell, local_ns)

        @needs_local_scope
        @line_magic("expl")
        def explain_analyze(self, line, cell='', local_ns={}):
            return self.execute("EXPLAIN ANALYZE " + line, cell, local_ns)


def load_ipython_extensions(ip):
    ip.register_magics(MediatumMagics)
    if SQLMagics:
        ip.register_magics(SqlMagic)
        ip.register_magics(SQLMagics)
        ip.magic("sql $SQLALCHEMY_CONNECTION")

load_ipython_extensions(ip)

ip.magic("autocall 1")
