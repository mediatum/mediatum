# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import pytest
from contenttypes.data import get_license_urls


def test_get_license_urls_valid():
    node = {"license": "license, http://example.com/license"}
    license_url, license_image_url = get_license_urls(node)
    assert license_url == "http://example.com/license"
    assert license_image_url == "/img/license.png"


@pytest.mark.parametrize("node", [
        {"license": "a"},
        {"license": "a,b"},
        {},
])
def test_get_license_urls_invalid(node):
    license_url, license_image_url = get_license_urls(node)
    assert license_url is None
    assert license_image_url is None
