# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class MultipleMatches(Exception):
    pass


class NoMatches(Exception):
    pass


def filter_scalar(predicate, seq):
    """Scans a sequence with `predicate` and returns a matched item.
    If no item matches, return None. If multiple items match, raise MultipleMatches
    :param predicate: callable taking a sequence element as argument and returning a true value for matches, like `filter`
    """
    found = [e for e in seq if predicate(e)]
    if len(found) > 1:
        raise MultipleMatches()
    if found:
        return found[0]


def filter_one(predicate, seq):
    """Scans a sequence with `predicate` and returns a matched item.
    If no item matches, raise NoMatches. If multiple items match, raise MultipleMatches
    :param predicate: callable taking a sequence element as argument and returning a true value for matches, like `filter`
    """
    found = [e for e in seq if predicate(e)]
    if len(found) > 1:
        raise MultipleMatches()
    if found:
        return found[0]
    raise NoMatches()
