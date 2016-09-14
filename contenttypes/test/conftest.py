# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from mediatumtal import tal
from core import config

tal.set_base(config.basedir)

from core.test.fixtures import req
from contenttypes.test.fixtures import *
