# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import functools as _functools
import json as _json
import logging as _logging

import backports as _backports
import backports.functools_lru_cache as _
try:
    import uwsgi as _uwsgi
except ImportError:
    _uwsgi = None
    loaded = False
else:
    loaded = True

import core as _core
import utils as _utils

_logg = _logging.getLogger(__name__)

_registered_signal_names = set()


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


@_backports.functools_lru_cache.lru_cache(maxsize=None)
def get_signal_number(name):
    """
    Allocate a new number for a uwsgi signal name.
    If that name already has a number, it will be returned.
    Otherwise, the name will be associated with a new number.
    This function may only be called with uwsgi loaded.
    """
    assert loaded
    if name in _registered_signal_names:
        raise RuntimeError("signal number with name {} already exists".format(name))
    _registered_signal_names.add(name)
    with _utils.locks.named_lock("uwsgi-signals"):
        @synchronize_number_in_cache("signals", name)
        def number(existing):
            return min(existing) - 1 if existing else 127
    if number < 1:
        raise RuntimeError("too many signals registered")
    return number


def register_signal_handler_for_worker(name):
    """
    Returns a decorator that registers the decorated function
    for the signal with the given name, so that subsequent
    invocations of the given signal will cause uwsgi to
    invoke the decorated function in the first available worker.
    `None` is returned, to indicate that the decorated
    function does not need to be called manually.
    If uwsgi is *not* loaded, nothing is registered,
    but the decorated function is returned unmodified,
    so it can be called manually later as needed.
    """
    def decorator(func):
        if not loaded:
            return func
        if not _uwsgi.worker_id():
            return
        signal = get_signal_number(name)
        @_functools.wraps(func)
        def wrapper(signal_):
            assert signal == signal_
            _logg.debug("calling uwsgi background worker %s (signal %s)", name, signal)
            try:
                result = func()
            except:
                _logg.exception("exception in uwsgi background worker %s (signal %s)", name, signal)
                _core.db.session.rollback()
            else:
                if result is None:
                    _logg.debug("uwsgi background worker %s (signal %s) done", name, signal)
                else:
                    _logg.warning(
                        "ignoring return value of uwsgi background worker %s (signal %s): %r",
                        name, signal, result,
                        )
        _uwsgi.register_signal(signal, "worker", wrapper)
    return decorator
