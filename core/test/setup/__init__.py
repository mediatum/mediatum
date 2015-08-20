# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import warnings

from core import config
from core.init import add_ustr_builtin, init_db, init_fulltext_search
logg = logging.getLogger(__name__)


def setup_basic():
    config.initialize("test_mediatum.cfg")
    add_ustr_builtin()
    init_db()
    warnings.simplefilter("always")
