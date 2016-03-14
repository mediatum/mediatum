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