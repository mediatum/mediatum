# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import unicodedata

import backports as _backports
import backports.functools_lru_cache as _

import core as _core
import core.config as _


@_backports.functools_lru_cache.lru_cache()
def get_skip_fields():
    """
    Generate list of attribute names that should not be public (via web service API).
    """
    return _core.config.getlist("services.raw-skip-metafields", default=("creator", "updateuser"))


def attribute_name_filter(attribute_name):
    """
    filter out system and admin-defined attributes
    """
    return (not attribute_name.startswith("system.")) and (attribute_name not in get_skip_fields())
