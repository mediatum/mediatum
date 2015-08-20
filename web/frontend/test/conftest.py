# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from core.test.setup import setup_basic

# WARNING: setup_basic() must be called before importing fixtures!
setup_basic()

from web.frontend.test.fixtures import *
from core.test.fixtures import collections
