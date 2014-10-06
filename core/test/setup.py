# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from core import config
from core.database.postgres import PostgresSQLAConnector
from core.init import load_system_types

db = None
logg = logging.getLogger(__name__)


def setup_test_db():
    global db
    config.initialize("test_mediatum.cfg")
    db = PostgresSQLAConnector()
    logg.info("setup_test_db")
    db.metadata.drop_all()
    db.metadata.create_all()
    import core
    core.db = db
    load_system_types()


