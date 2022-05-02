# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details

    Common mediaTUM exceptions. More to come...
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class MediatumException(Exception):
    pass


class SecurityException(MediatumException):
    pass
