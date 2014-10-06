# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function
import warnings
from contextlib import contextmanager


def assert_node(node, **kw):
    for attr in ["name", "type", "schema"]:
        if attr in kw:
            value = kw.pop(attr)
            assert getattr(node, attr) == value
    assert node.attrs == kw


def assert_deprecation_warning(func, *args, **kwargs):
    with warnings.catch_warnings(record=True) as w:
        ret = func(*args, **kwargs)
        assert len(w) == 1, "no DeprecationWarning in " + func.__name__
        assert issubclass(w[0].category, DeprecationWarning)
    return ret
