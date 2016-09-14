# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from utils.testing import test_setup

test_setup()

# global fixtures, do not import them again!
from core.test.fixtures import *

print logging.getLogger().level