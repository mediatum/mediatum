# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division
from __future__ import print_function

from functools import wraps, partial
import logging 
import re


logg = logging.getLogger(__name__)


def uu(s):
    pass


class EncodingException(Exception):
    pass


def ensure_unicode_returned(f=None, name=None, silent=False):
    """
    
    """
    if f is None:
        return partial(ensure_unicode_returned, name=name, silent=silent)
    
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
            if not silent:
                logg.warning("return value of '%s': expected unicode, got value of type %s: '%s'", _name, type(res), res)
            return unicode(res)
        else:
            if not silent:
                logg.warning(
                    "return value of '%s': expected unicode, trying to decode ustr as utf8: %s",
                    _name,
                    res[:200].encode("string-escape"),
                )
            return res.decode("utf8")
    return _wrapper


def ensure_unicode(s, silent=False):
    if isinstance(s, unicode):
        return s
    elif not isinstance(s, str):
        if not silent:
            logg.warning("expected unicode, got value of type %s: '%s'", type(s), s)
        return unicode(s)
    else:
        if not silent:
            logg.warning("trying to decode ustr as utf8: %s", s[:200].encode("string-escape"))
        return s.decode("utf8")


@ensure_unicode_returned
def replace_attribute_variables(value, nid, value_getter, reg_exp, left_tag, right_tag):
    for var in re.findall(reg_exp, value):
        if var == "att:id":
            value = value.replace(left_tag + var + right_tag, unicode(nid))
        elif var.startswith("att:"):
            val = value_getter(var[4:])
            if val == "":
                val = "____"
            value = value.replace(left_tag + var + right_tag, val)
    return value
