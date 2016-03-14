# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import fixture
from mock import MagicMock


@fixture
def req():
    """XXX: Very simple mock request, improve this"""
    req = MagicMock()
    req.header = ["0", "1", "2", "3", "4", "5"]
    req.session = {}
    req.params = {}
    req.form = {}
    req.args = {}
    req.path = "/"
    req.request = {}
    return req


@fixture
def user():
    """XXX: Very simple mock user, improve this"""
    return MagicMock(name="user")


@fixture
def nav_frame():
    """XXX: Very simple mock navigation frame, improve this"""
    return MagicMock(name="navigation_frame")
