# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import urllib
import pytest
import utils.url


def test_urlencode_params_to_query():
    params = {u"arg1": u"üni",
              "arg2": 42,
              "": "blah",
              "empty": ""}
    res = utils.url.urlencode_params_to_query(params)
    assert res == "arg1=" + urllib.quote("ü") + "ni&arg2=42"


@pytest.mark.parametrize("path, params, expected", [
                            ("/", {}, "/"),
                            ("testpath", {}, "testpath"),
                            ("/testpath", {}, "/testpath"),
                            ("/testpath", {"": ""}, "/testpath"),
                            ("/testpath", {"arg1": 6, "arg2": "blah"}, "/testpath?arg1=6&arg2=blah"),
                        ])
def test_build_url_from_path_and_param(path, params, expected):
    assert utils.url.build_url_from_path_and_params(path, params) == expected


def test_add_params_to_url_start_with_plain_url():
    params = {"b": "test"}
    assert utils.url.add_query_params_to_url("http://example.com", params) == "http://example.com?b=test"


def test_add_params_to_url_existing_params():
    params = {"a": 5}
    res = utils.url.add_query_params_to_url("http://example.com?b=test", params)
    assert res == "http://example.com?a=5&b=test" or res == "http://example.com?b=test&a=5"