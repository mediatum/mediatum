# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import warnings

from core import config
from core.database.postgres import PostgresSQLAConnector
from core.init import load_system_types
logg = logging.getLogger(__name__)


def setup_basic():
    config.initialize("test_mediatum.cfg")
    warnings.simplefilter("always")


def setup_with_db():
    setup_basic()
    db = PostgresSQLAConnector()
    logg.info("setup_test_db")
    db.metadata.drop_all()
    db.metadata.create_all()
    import core
    core.db = db
    load_system_types()
