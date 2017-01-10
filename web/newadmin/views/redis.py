# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from flask_admin.contrib.rediscli import RedisCli
from flask.ext import login


class ProtectedRedisCli(RedisCli):

    def is_accessible(self):
        return login.current_user.is_authenticated and login.current_user.is_admin