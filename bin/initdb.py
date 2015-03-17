# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function

import logging
from core.init import basic_init
basic_init()

logg = logging.getLogger(__name__)

from core.database.init import init_database_values
from core import db

logg.info("creating DB schema...")
db.create_all()
s = db.session
logg.info("loading default values...")
init_database_values(db.session)
s.commit()
logg.info("commit")
