# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
    
    Various handlers for testing handlers.
"""
from __future__ import division

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
