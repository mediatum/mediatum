# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
    Various functions for checking and converting unsafe user input.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging


logg = logging.getLogger(__name__)


def string_to_int(data):
    if data is None:
        logg.warning("cannot convert None value to an integer")
        return None
    try:
        nid = int(data)
    except ValueError:
        logg.warning("invalid user input for int: '%r'", data)
        return None

    return nid
