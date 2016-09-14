# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details

    Various functions for checking and converting unsafe user input.
"""
from __future__ import absolute_import
import logging


logg = logging.getLogger(__name__)


def string_to_int(data):
    if data is None:
        logg.warn("cannot convert None value to an integer")
        return None
    try:
        nid = int(data)
    except ValueError:
        logg.warn("invalid user input for int: '%r'", data)
        return None

    return nid


