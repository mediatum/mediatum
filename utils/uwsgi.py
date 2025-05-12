# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import json as _json
import logging as _logging

try:
    import uwsgi as _uwsgi
except ImportError:
    _uwsgi = None
    loaded = False
else:
    loaded = True

_logg = _logging.getLogger(__name__)


def synchronize_number_in_cache(cache_name, number_name):
    """
    Return a decorator for a number-generating function `func`.
    The decorator looks for the number with the given
    `number_name` in the uwsgi cache with the given `cache_name`.
    If it is not found, `func` is called with all existing
    numbers in the cache (as frozenset) and is expected to return
    a new number; that is then registered with the `number_name`.
    The number for the `number_name`
    (after retrieved, or after generated)
    is then *returned by the decorator*, i.e.,
    the decorated function is replaced by the number!
    The decorator, i.e. the act of decoration,
    must be protected by a `cache_name`-specific uwsgi lock!
    This function may only be called with uwsgi loaded.
    """
    assert loaded
    def decorator(get_new_number):
        name2number = _json.loads(_uwsgi.cache_get(cache_name) or "{}")
        if number_name not in name2number:
            number = get_new_number(frozenset(name2number.values()))
            _logg.debug("storing new uwsgi number %s=%s in cache %s", number_name, number, cache_name)
            name2number[number_name] = number
            _uwsgi.cache_update(cache_name, _json.dumps(name2number))
        return name2number[number_name]
    return decorator
