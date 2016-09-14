# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import pytest
from pytest import fixture

from web.frontend import main
from core.transition import httpstatus

@fixture
def language_config_setting(monkeypatch):
    import core.config
    monkeypatch.setattr(core.config, "languages", ["de", "no"])


@fixture(params=[
    main.display,
    main.display_noframe,
    main.publish,
    main.display_alias,
    main.display_newstyle,
    main.show_parent_node,
    main.display_404
])
def all_frontend_handlers(request):
    return request.param


def test_change_language_request_no_change(req):
    assert main.change_language_request(req) is None


def test_change_language_request_change(req, language_config_setting):
    req.path = "/testpath"
    req.args = {u"testarg": u"5"}
    req.args["change_language"] = "no"
    assert main.change_language_request(req) == httpstatus.HTTP_MOVED_TEMPORARILY
    assert req.Cookies["language"] == "no"
    assert req.request["Location"] == "/testpath?testarg=5"


def test_change_language_request_invalid_lang(req, language_config_setting):
    req.path = "/testpath"
    req.args = {u"testarg": u"5"}
    req.args["change_language"] = "haha"
    assert main.change_language_request(req) == httpstatus.HTTP_MOVED_TEMPORARILY
    assert req.Cookies.get("language") != "haha"
    assert req.request["Location"] == "/testpath?testarg=5"


def test_change_language_all_handlers(req, all_frontend_handlers):
    handler = all_frontend_handlers
    req.args["change_language"] = "de"
    code = handler(req)
    assert code == httpstatus.HTTP_MOVED_TEMPORARILY
    assert req.Cookies["language"] == "de"
