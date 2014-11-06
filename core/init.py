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
import pkgutil
import importlib
import logging
import locale
from pprint import pformat

import core.config as config
from core.node import Root, Metadatatypes


logg = logging.getLogger(__name__)


def set_locale():
    # locale setting for sorting, default to system locale
    loc = locale.setlocale(locale.LC_COLLATE, '')
    logg.info("using locale %s for sorting", loc)


def load_content_types():
    from contenttypes import *


def register_node_classes():
    from contenttypes.default import Default
    tree.registerNodeClass("default", Default)

    from contenttypes.directory import Directory
    tree.registerNodeClass("directory", Directory)
    from contenttypes.project import Project
    tree.registerNodeClass("project", Project)
    tree.registerNodeClass("collection", Directory)
    tree.registerNodeClass("collections", Directory)
    tree.registerNodeClass("root", Root)
    tree.registerNodeClass("home", Directory)

    # user
    from core.user import User
    tree.registerNodeClass("user", User)
    from core.usergroup import UserGroup
    tree.registerNodeClass("usergroup", UserGroup)

    # meta
    from schema.schema import Metadatatype, Metadatafield, Mask, Maskitem
    tree.registerNodeClass("metadatatypes", Metadatatypes)
    tree.registerNodeClass("metadatatype", Metadatatype)
    tree.registerNodeClass("metafield", Metadatafield)
    tree.registerNodeClass("mask", Mask)
    tree.registerNodeClass("maskitem", Maskitem)
    from schema.searchmask import SearchMaskItem
    tree.registerNodeClass("searchmaskitem", SearchMaskItem)

    # shoppingbag
    from core.shoppingbag import ShoppingBag
    tree.registerNodeClass("shoppingbag", ShoppingBag)


def register_node_functions():
    import schema.schema as schema
    tree.registerNodeFunction("getMetaFields", schema.node_getMetaFields)
    tree.registerNodeFunction("getMetaField", schema.node_getMetaField)
    tree.registerNodeFunction("getSearchFields", schema.node_getSearchFields)
    tree.registerNodeFunction("getSortFields", schema.node_getSortFields)
    tree.registerNodeFunction("getMasks", schema.node_getMasks)
    tree.registerNodeFunction("getMask", schema.node_getMask)
    tree.registerNodeFunction("getDescription", schema.node_getDescription)


def init_register_mapping_field():
    from schema.mapping import Mapping, MappingField
    tree.registerNodeClass("mapping", Mapping)
    tree.registerNodeClass("mappingfield", MappingField)


def register_workflow():
    from workflow import workflow
    workflow.register()
#     workflow.register_nodeclasses()


def init_ldap():
    # LDAP activated
    if config.get("ldap.activate", "").lower() == "true":
        print "activate LDAP login"
        from core.userldap import LDAPUser
        import core.users as users
        users.registerAuthenticator(LDAPUser(), "ldapuser")


def init_archivemanager():
    # load archive manager
    global archivemanager
    archivemanager = None
    try:
        import core.archive as archive
        archive.archivemanager = archive.ArchiveManager()
    except ImportError:
        logg.error("error while initialization of archive manager", exc_info=1)


def tal_setup():
    from mediatumtal import tal
    tal.set_base(config.basedir)


def log_basic_sys_info():
    logg.info("Python Version is %s", sys.version.split("\n")[0])
    logg.info("Base path is at %s", config.basedir)
    logg.info("sys.path is:\n%s", pformat(sys.path))


def check_imports():
    logg.info("testing external imports:")
    external_modules = [
        "PIL",
        "requests",
        "lxml",
        "werkzeug",
        "jinja2",
        "pyjade",
        "coffeescript",
        "yaml",
        "pyaml",
        "babel",
        "mediatumfsm",
        "mediatumtal",
        "mediatumbabel"
    ]

    for modname in external_modules:
        mod = importlib.import_module(modname)
        logg.info("import %s: version '%s'", mod, mod.__version__ if hasattr(mod, "__version__") else "unknown")


def init_app():
    from core.transition.app import create_app
    import core
    core.app, core.db = create_app()


def init_modules():
    """init modules with own init function"""
    from contenttypes.default import init_maskcache
    init_maskcache()
    from export import oaisets
#     oaisets.init()
    from schema import schema
    schema.init()
    from core import xmlnode
#     xmlnode.init()
    from core.plugins import init_plugins
    init_plugins()


def add_ustr_builtin():
    inspection_log = logging.getLogger("inspection")
    
    def ustr(s):
        if isinstance(s, unicode):
            inspection_log.warn("ustr() called on unicode object, ignoring '%s'", s)
            return s
    #     elif isinstance(s, int):
    #         logg.warn("ustr() called on int object '%s'", s)
        
        return str(s)
        
    import __builtin__
    __builtin__.ustr  = ustr


def basic_init():
    add_ustr_builtin()
    import core.config
    core.config.initialize()
    import utils.log
    utils.log.initialize()
    log_basic_sys_info()
    check_imports()
    set_locale()
    init_app()
#     register_node_classes()
#     register_node_functions()
    load_content_types()


def full_init():
    basic_init()
#     init_register_mapping_field()
#     register_workflow()
    init_ldap()
    init_archivemanager()
    init_modules()
    tal_setup()
