from __future__ import division

import logging as _logging
try:
    import uwsgi as _uwsgi
except ImportError:
    _uwsgi = None
    import threading as _threading


_logg = _logging.getLogger(__name__)
_locks = {}


class _UwsgiLock():
    """to use uwsgi lock with context manager"""
    def __init__(self, number):
        self.number = number

    def __enter__(self):
        return _uwsgi.lock(self.number)

    def __exit__(self, *args):
        _uwsgi.unlock(self.number)

def register_lock(name, number):
    """lock centrally or locally can be registered by name and number"""
    if name in _locks:
        raise RuntimeError(u"lock name '{}' already exists!".format(name))
    if number in _locks.values():
        raise RuntimeError(u"lock number '{}' already exists!".format(number))

    _logg.debug("Lock %s is registered with number %s", name, number)
    if _uwsgi:
        _locks[name] = _UwsgiLock(number)
    else:
        _locks[name] = _threading.Lock()

def named_lock(name):
    """get a lock by name"""
    if name not in _locks.keys():
        raise RuntimeError(u"lock name '{}' does not exist!".format(name))
    return _locks[name]
