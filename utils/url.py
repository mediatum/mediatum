# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import urllib

def urlencode_params_to_query(params):
    """
    URL-encodes a dict as URL query string. Values are coerced into UTF8 strings.
    :returns: url-encoded UTF8 string
    """
    params = {k: unicode(v).encode("utf8") for k, v in params.items() if k and v}
    return urllib.urlencode(params)


def build_url_from_path_and_params(path, params):
    """
    :param path: URL path
    :param params: parameter dict for the URL query
    """
    encoded_params = urlencode_params_to_query(params)
    if encoded_params:
        return path + "?" + urlencode_params_to_query(params)
    else:
        return path