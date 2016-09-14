# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
    
    Various handlers for testing handlers.
"""
import random
import string


def error(req):
    raise Exception("this is a test!")


def error_variable_msg(req):
    random_string = ''.join(random.choice(string.ascii_uppercase) for _ in range(6))
    raise Exception("this is a test exception with random stuff:" + random_string)


def db_error(req):
    from core import db
    random_sql = '|'.join(random.choice(string.ascii_uppercase) for _ in range(6))
    db.session.execute(random_sql)