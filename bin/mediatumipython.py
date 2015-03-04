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

SQL
---

See `ipython-sql documentation <https://pypi.python.org/pypi/ipython-sql>`_

.. code:: sql
    
    // select nodes with no parents
    %sql SELECT * FROM node where id NOT IN (SELECT cid FROM nodemapping)
'''
from __future__ import division, absolute_import, print_function
import logging
import sys

from sqlalchemy.sql import *
from sqlalchemy.orm.exc import NoResultFound

from core.database.postgres import *
from utils.compat import *

from core import config
import core.init as initmodule
from functools import wraps

from core import init
import core.database
init.basic_init()

from core import Node
from core.file import File

q = core.db.query
s = core.db.session
conn = core.db.conn

### settings

# set this to INFO for SQL statement echo, DEBUG for even more info from SQLAlchemy
SQLALCHEMY_LOGGING = logging.WARN

# use default connection specified by mediatum config for ipython-sql
SQLALCHEMY_CONNECTION = core.db.connectstr
# TODO: changing the connection string should be possible for the postgres connector, too

# load types for interactive querying
from contenttypes import Audio, ContentType, Directory, Collection, ContainerType, Collections, Home, Document, Flash, Image, Imagestream, \
    Project, Video, Data
from core.systemtypes import Mappings, Metadatatypes, Root, Users, UserGroups, Navigation, Searchmasks, ExternalUsers
from schema.schema import Metadatatype, Maskitem, Mask, Metafield


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

# IPython magic

from IPython.core.magic import Magics, magics_class, line_magic
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

    @line_magic
    def l(self, line):
        print(cnode)
        section_names = ["Parents", "Subnodes", "Attributes", "Files"]
        section_lines = [
            [u"{} {}:  {}".format(n.id, n.name, n.type) for n in cnode.parents],
            [u"{} {}:  {}".format(n.id, n.name, n.type) for n in cnode.children],
            [u"{} = {}".format(name, value) for name, value in iteritems(cnode.attrs)],
            [u"{} {} {}".format(a.path, a.filetype, a.mimetype) for a in cnode.files]
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
        try:
            child = cnode.children.filter_by(id=long(args.nid)).one()
        except NoResultFound:
            print(u"Child {} not found!".format(args.nid))
            return
        cnode.children.remove(child)

    @needs_init("basic")
    @magic_arguments()
    @argument("nid")
    @line_magic
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


def load_ipython_extension(ip):
    """Load the extension in IPython."""
    ip.register_magics(MediatumMagics)

load_ipython_extension(ip)

# mediaTUM

ip.magic("autocall 1")

try:
    ip.magic("reload_ext sql")
    ip.magic("sql $SQLALCHEMY_CONNECTION")
except ImportError:
    print("SQL magic not found! You should install the IPython sql extension: pip install ipython-sql")
