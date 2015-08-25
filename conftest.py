# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import logging
import warnings
from pytest import skip
from utils.log import TraceLogger

TraceLogger.skip_trace_lines += ("pytest", )
# TraceLogger.stop_trace_at = tuple()


def pytest_addoption(parser):
    parser.addoption('--slow', action='store_true', default=False,
                     help='Also run slow tests')


def pytest_runtest_setup(item):
    """Skip tests if they are marked as slow and --slow is not given"""
    if getattr(item.obj, 'slow', None) and not item.config.getvalue('slow'):
        skip('slow tests not requested')


from core import config
from core.init import add_ustr_builtin, init_db
config.initialize("test_mediatum.cfg")
add_ustr_builtin()
import utils.log
utils.log.initialize()
init_db()
from core import db
db.disable_session_for_test()
warnings.simplefilter("always")

# global fixtures, do not import them again!
from core.test.fixtures import *

print logging.getLogger().level
