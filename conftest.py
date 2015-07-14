# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function




import pytest

def pytest_addoption(parser):
    parser.addoption('--slow', action='store_true', default=False,
                      help='Also run slow tests')

def pytest_runtest_setup(item):
    """Skip tests if they are marked as slow and --slow is not given"""
    if getattr(item.obj, 'slow', None) and not item.config.getvalue('slow'):
        pytest.skip('slow tests not requested')
        