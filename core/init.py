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
import importlib
import logging
import locale
from pprint import pformat

import core.config as config


logg = logging.getLogger(__name__)


def set_locale():
    # locale setting, default to system locale
    # XXX: do we need this?
    loc = locale.setlocale(locale.LC_COLLATE, '')
    logg.debug("using locale %s", loc)


def load_system_types():
    from core.systemtypes import *
    from schema.searchmask import SearchMaskItem, SearchMask
    from schema.mapping import Mapping, MappingField
    from core import ShoppingBag


def load_types():
    from contenttypes import *


def register_workflow():
    from workflow import workflow
    workflow.register()


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
    logg.info("Python Version is %s, base path ist at %s", sys.version.split("\n")[0], config.basedir)
    logg.debug("sys.path is\n%s", pformat(sys.path))


def check_imports():
    external_modules = [
        "babel",
        "coffeescript",
        "decorator",
        "httplib2",
        "ipaddr",
        "jinja2",
        "Levenshtein",
        "logstash",
        "lxml",
        "mediatumbabel",
        "mediatumfsm",
        "mediatumtal",
        "mock",
        "parcon",
        "PIL",
        "psycopg2",
        "pyaml",
        "pydot",
        "pyjade",
        "pymarc",
        "pyPdf",
        "reportlab",
        "requests",
        "scrypt",
        "sqlalchemy",
        "sqlalchemy_utils",
        "unicodecsv",
        "werkzeug",
        "yaml",
    ]

    for modname in external_modules:
        mod = importlib.import_module(modname)
        logg.debug("import version '%s' of %s", mod.__version__ if hasattr(mod, "__version__") else "unknown", mod)


def init_app():
    from core.transition.app import create_app
    import core
    core.app = create_app()


def init_db_connector():
    import core.database  # init DB connector
    # assign model classes for selected DB connector to the core package
    for cls in core.db.get_model_classes():
        setattr(core, cls.__name__, cls)


def connect_db(force_test_db=None):
    import core
    core.db.configure(force_test_db)
    core.db.create_engine()


def init_fulltext_search():
    import core
    core.db.init_fulltext_search()


def init_modules():
    """init modules with own init function"""
    from contenttypes.data import init_maskcache
    init_maskcache()
    from export import oaisets
#     oaisets.init()
    from schema import schema
    schema.init()
    from core import xmlnode
#     xmlnode.init()
    from core import auth
    auth.init()
    from export import exportutils
    exportutils.init()
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
    __builtin__.ustr = ustr


def check_undefined_nodeclasses(stub_undefined_nodetypes=None, fail_if_undefined_nodetypes=None, ignore_nodetypes=[]):
    """Checks if all nodetypes found in the database are defined as subclasses of Node.

    There are 3 modes which can be selected in the config file or by the parameters:

    * fail_if_undefined_nodetypes is True:
        => raise an Exception if a class if missing. Recommended.

    * fail_if_undefined_nodetypes is False, stub_undefined_nodetypes is True:
        => emit a warning that classes are missing and create stub classes directly inheriting from Node.
        Most code will continue to work, but it may fail if the real class overrides methods from Node.

    * fail_if_undefined_nodetypes is False, stub_undefined_nodetypes is False (default):
        => just emit a warning that classes are missing
    """
    from core import Node, db

    known_nodetypes = set(c.__mapper__.polymorphic_identity for c in Node.get_all_subclasses())
    nodetypes_in_db = set(t[0] for t in db.query(Node.type.distinct()))
    undefined_nodetypes = nodetypes_in_db - known_nodetypes - set(ignore_nodetypes)

    if undefined_nodetypes:

        if fail_if_undefined_nodetypes is None:
            fail_if_undefined_nodetypes = config.get("config.fail_if_undefined_nodetypes", "false") == "true"

        msg = u"some node types are present in the database, but not defined in code. Missing plugins?\n{}".format(undefined_nodetypes)

        if fail_if_undefined_nodetypes:
            raise Exception(msg)
        else:
            logg.warn(msg)

        if stub_undefined_nodetypes is None:
            stub_undefined_nodetypes = config.get("config.stub_undefined_nodetypes", "false") == "true"

        if stub_undefined_nodetypes:
            for t in undefined_nodetypes:
                clsname = t.capitalize()
                type(str(clsname), (Node, ), {})
                logg.info("auto-generated stub class for node type '%s'", clsname)


def basic_init(root_loglevel=None, config_filepath=None, log_filepath=None, use_logstash=None, force_test_db=None):
    add_ustr_builtin()
    import core.config
    core.config.initialize(config_filepath)
    import utils.log
    utils.log.initialize(root_loglevel, log_filepath, use_logstash)
    log_basic_sys_info()
    check_imports()
    set_locale()
    init_app()
    init_db_connector()
    load_system_types()
    load_types()
    connect_db(force_test_db)


def additional_init():
    from core import db
    from core.database import validity
    db.check_db_structure_validity()
    validity.check_database()
    check_undefined_nodeclasses()
    init_fulltext_search()
    register_workflow()
    init_ldap()
    init_archivemanager()
    init_modules()
    tal_setup()


def full_init(root_loglevel=None, config_filepath=None, log_filepath=None, use_logstash=None, force_test_db=None):
    basic_init(root_loglevel, config_filepath, log_filepath, use_logstash, force_test_db)
    additional_init()
