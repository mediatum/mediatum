# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import warnings

from core import config
from core.init import load_system_types, load_types
logg = logging.getLogger(__name__)


def setup_basic():
    config.initialize("test_mediatum.cfg")
    warnings.simplefilter("always")
