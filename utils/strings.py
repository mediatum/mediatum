# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from functools import wraps, partial
import logging 


logg = logging.getLogger(__name__)


def uu(s):
    pass


class EncodingException(Exception):
    pass


def ensure_unicode_returned(f=None, name=None):
    """
    
    """
    if f is None:
        return partial(ensure_unicode_returned, name=name)
    
    if name is None:
        _name = f.__name__
    else:
        _name = name
    
    @wraps(f)
    def _wrapper(*args, **kwargs):
        res = f(*args, **kwargs)
        if isinstance(res, unicode):
            return res
        elif not isinstance(res, str):
            logg.warn("return value of '%s': expected unicode, got value of type %s: '%s'", _name, type(res), res)
            return unicode(res)
        else:
            logg.warn("return value of '%s': expected unicode, trying to decode str as utf8: %s", _name, res.encode("string-escape"))
            return unicode(res, encoding="utf8")
    return _wrapper
