# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from web.edit.edit import edit_print
import web.edit.edit


def test_edit_print(req, monkeypatch):
    req.path = "/print/123_test.pdf"

    class TestEditModule(object):

        def getPrintView(self, nid, additional_data, req):
            return "test_{}".format(nid, additional_data)

    monkeypatch.setattr(web.edit.edit, "getEditModules", lambda: {"test": TestEditModule()})
    edit_print(req)
    assert req.text == "test_123"


def test_edit_print_additional_data(req, monkeypatch):
    req.path = "/print/123_test_data.pdf"

    class TestEditModule(object):

        def getPrintView(self, nid, additional_data, req):
            return "test_{}_{}".format(nid, additional_data)

    monkeypatch.setattr(web.edit.edit, "getEditModules", lambda: {"test": TestEditModule()})
    edit_print(req)
    assert req.text == "test_123_data"