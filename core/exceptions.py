# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
    Common mediaTUM exceptions. More to come...
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class MediatumException(Exception):
    pass


class SecurityException(MediatumException):
    pass
