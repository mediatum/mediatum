# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import warnings


def assert_node(node, **kw):
    for attr in ["name", "type", "schema"]:
        if attr in kw:
            value = kw.pop(attr)
            assert getattr(node, attr) == value
    assert node.attrs == kw


def _assert_deprecation_warning(func, max_count=1, *args, **kwargs):
    with warnings.catch_warnings(record=True) as w:
        ret = func(*args, **kwargs)
        assert len(w) > 0, "no DeprecationWarning in " + func.__name__
        assert issubclass(w[0].category, DeprecationWarning)
        if max_count > 1:
            assert len(w) <= max_count, "more than {} DeprecationWarning({}) in {}".format(max_count, len(w), func.__name__)
    return ret


def assert_deprecation_warning(func, *args, **kwargs):
    return _assert_deprecation_warning(func, 1, *args, **kwargs)


def assert_deprecation_warning_allow_multiple(func, max_count, *args, **kwargs):
    return _assert_deprecation_warning(func, max_count, *args, **kwargs)


def assert_sorted(seq, cmp=None, key=None, reverse=False):
    sorted_seq = sorted(seq, cmp, key, reverse)
    if key:
        # provide better feedback in the common case with a given sort key
        assert seq == sorted_seq, "got key seq {}, expected {}".format([key(e) for e in seq], [key(e) for e in sorted_seq])
    else:
        assert seq == sorted_seq
