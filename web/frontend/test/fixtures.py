# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import fixture, yield_fixture
from mock import MagicMock
from core.transition import current_app
from core.transition.app import AthanaFlaskStyleApp


@fixture
def user():
    """XXX: Very simple mock user, improve this"""
    return MagicMock(name="user")


@fixture
def nav_frame():
    """XXX: Very simple mock navigation frame, improve this"""
    return MagicMock(name="navigation_frame")
