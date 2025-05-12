# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging as _logging
import threading as _threading

import backports as _backports
import backports.functools_lru_cache as _

try:
    import uwsgi as _uwsgi
except ImportError:
    _uwsgi = None

_logg = _logging.getLogger(__name__)

import utils as _utils
import utils.uwsgi as _


class _UwsgiLock():
    """to use uwsgi lock with context manager"""
    def __init__(self, number):
        self.number = number

    def __enter__(self):
        return _uwsgi.lock(self.number)

    def __exit__(self, *args):
        _uwsgi.unlock(self.number)


@_backports.functools_lru_cache.lru_cache(maxsize=None)
def named_lock(name):
    """get a lock by name"""
    _logg.debug("preparing new lock '%s'", name)
    if _uwsgi is None:
        return _threading.Lock()
    with _UwsgiLock(0):
        @_utils.uwsgi.synchronize_number_in_cache("locks", name)
        def number(existing):
            return max(existing) + 1 if existing else 1
    return _UwsgiLock(number)
