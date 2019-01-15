import threading as _threading
import logging as _logging


_logg = _logging.getLogger(__name__)
_locks = {}


def register_lock(name):
    # lock centrally or locally is registered by name
    if name in _locks:
        raise RuntimeError(u"lock name '{}' already exists!".format(name))
    _logg.debug("Lock %s registered", name)
    _locks[name] = _threading.Lock()

def named_lock(name):
    # get a lock by name
    if name not in _locks:
        raise RuntimeError(u"lock name '{}' does not exist!".format(name))
    return _locks[name]
