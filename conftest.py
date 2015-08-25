# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import logging
import warnings
from pytest import skip
from utils.log import TraceLogger, ConsoleHandler, ROOT_STREAM_LOGFORMAT


root_logger = logging.getLogger()
stream_handler = ConsoleHandler()
stream_handler.setFormatter(logging.Formatter(ROOT_STREAM_LOGFORMAT))
root_logger.handlers = []
root_logger.addHandler(stream_handler)
TraceLogger.skip_trace_lines += ("pytest", )
# TraceLogger.stop_trace_at = tuple()
logging.setLoggerClass(TraceLogger)
logging.captureWarnings(True)


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
init_db()
from core import db
db.disable_session_for_test()
warnings.simplefilter("always")

# global fixtures, do not import them again!
from core.test.fixtures import *
