# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
    Various handlers for testing handlers.
"""

from __future__ import division
from __future__ import print_function

import string
import utils.utils as _utils_utils


def error(req):
    raise Exception("this is a test!")


def error_variable_msg(req):
    random_string = _utils_utils.gen_secure_token(128)
    raise Exception("this is a test exception with random stuff:" + random_string)


def db_error(req):
    from core import db
    random_sql = '|'.join(_utils_utils.gen_secure_token(128))
    db.session.execute(random_sql)
