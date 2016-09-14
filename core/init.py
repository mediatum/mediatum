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
from functools import wraps
import sys
import importlib
import logging
import locale
from pprint import pformat

import core.config as config


logg = logging.getLogger(__name__)

# functions can check if mediaTUM is initialized correctly and report an error if this is not the case

INIT_STATES = {
    None: 0,  # nothing initialized
    "basic": 100,  # core.init.basic_init()
    "full": 200  # core.init.full_init()
}

REV_INIT_STATES = {v: k for k, v in INIT_STATES.items()}

CURRENT_INIT_STATE = INIT_STATES[None]


def init_state_reached(min_state):
    if CURRENT_INIT_STATE >= INIT_STATES[min_state]:
        logg.debug("Current init state is '%s', requested state '%s', doing nothing.",
                   REV_INIT_STATES[CURRENT_INIT_STATE], min_state)
        return True
    return False


def get_current_init_state():
    """Returns string representation for current init state or None if nothing has been initialized yet."""
    return REV_INIT_STATES[CURRENT_INIT_STATE]


def _set_current_init_state(state):
    """Set current init state by string representation"""
    global CURRENT_INIT_STATE
    CURRENT_INIT_STATE = INIT_STATES[state]


def set_locale():
    # locale setting, default to system locale
    # XXX: do we need this?
    loc = locale.setlocale(locale.LC_COLLATE, '')
    logg.debug("using locale %s", loc)


def load_system_types():
    from core.systemtypes import *
    from schema.searchmask import SearchMaskItem, SearchMask
    from schema.mapping import Mapping, MappingField


def load_types():
    from contenttypes import *


def register_workflow():
    from workflow import workflow
    workflow.register()


def tal_setup():
    from mediatumtal import tal
    tal.set_base(config.basedir)


def log_basic_sys_info():
    logg.info("Python Version is %s, base path ist at %s", sys.version.split("\n")[0], config.basedir)
    logg.debug("sys.path is\n%s", pformat(sys.path))


def check_imports():
    external_modules = [
        "alembic",
        "coffeescript",
        "configargparse",
        "decorator",
        "exiftool",
        "flask_admin",
        "httplib2",
        "humanize",
        "ipaddr",
        "jinja2",
        "Levenshtein",
        "logstash",
        "lxml",
        "mediatumbabel",
        "mediatumfsm",
        "mediatumtal",
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
        "sqlalchemy_continuum",
        "sqlalchemy_utils",
        "sympy",
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
    import core
    from core.database.postgres.connector import PostgresSQLAConnector  # init DB connector
    core.db = PostgresSQLAConnector()
    # assign model classes for selected DB connector to the core package
    for cls in core.db.get_model_classes():
        setattr(core, cls.__name__, cls)


def connect_db(force_test_db=None, automigrate=False):
    import core
    core.db.configure(force_test_db)
    core.db.create_engine()

    if automigrate:
        core.db.upgrade_schema()


def init_fulltext_search():
    import core
    core.db.init_fulltext_search()


def init_modules():
    """init modules with own init function"""
    from export import oaisets
    oaisets.init()
    from export import exportutils
    exportutils.init()
    from schema import schema
    schema.init()
    from core import xmlnode
#     xmlnode.init()
    from core import auth
    auth.init()
    from export import exportutils
    exportutils.init()


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


def update_nodetypes_in_db():
    """The DB must know which nodetypes exist and if they are a container or a content node type.
    Node types are never deleted from the DB, only added.

    We still have some "system node types" which don't fit in either category.
    They will be moved to their own tables later.
    """
    from contenttypes import Content, Container
    from core import db, NodeType
    q = db.query
    s = db.session

    db_nodetypes = set(t[0] for t in q(NodeType.name))

    for cls in Content.get_all_subclasses():
        typename = cls.__mapper__.polymorphic_identity
        if typename not in db_nodetypes:
            s.add(NodeType(name=unicode(typename), is_container=False))
            logg.debug("added new content type '%s' to DB", typename)

    for cls in Container.get_all_subclasses():
        typename = cls.__mapper__.polymorphic_identity
        if typename not in db_nodetypes:
            s.add(NodeType(name=unicode(typename), is_container=True))
            logg.debug("added new container type '%s' to DB", typename)

    s.commit()


def basic_init(root_loglevel=None, config_filepath=None, prefer_config_filename=None, log_filepath=None, log_filename=None,
               use_logstash=None, force_test_db=None, automigrate=False):
    init_state = "basic"
    if init_state_reached(init_state):
        return

    add_ustr_builtin()
    import core.config
    core.config.initialize(config_filepath, prefer_config_filename)
    import utils.log
    utils.log.initialize(root_loglevel, log_filepath, log_filename, use_logstash)
    log_basic_sys_info()
    check_imports()
    set_locale()
    init_app()
    init_db_connector()
    load_system_types()
    load_types()
    connect_db(force_test_db, automigrate)
    _set_current_init_state(init_state)
    from core import db
    db.session.rollback()


def _additional_init():
    from core import db
    from core.database import validity
    db.check_db_structure_validity()
    validity.check_database()
    register_workflow()
    from core import plugins
    init_modules()
    plugins.init_plugins()
    check_undefined_nodeclasses()
    update_nodetypes_in_db()
    init_fulltext_search()
    tal_setup()
    db.session.rollback()


def full_init(root_loglevel=None, config_filepath=None, prefer_config_filename=None, log_filepath=None, log_filename=None,
              use_logstash=None, force_test_db=None, automigrate=False):
    init_state = "full"
    if init_state_reached(init_state):
        return

    basic_init(root_loglevel, config_filepath, log_filepath, log_filename, prefer_config_filename, use_logstash, force_test_db, automigrate)
    _additional_init()
    _set_current_init_state(init_state)
