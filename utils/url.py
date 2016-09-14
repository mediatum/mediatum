# -*- coding: utf-8 -*-

"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import urllib
import urlparse


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


def add_query_params_to_url(url, params):
    """
    Adds query key=value pairs to a given URL, keeping the contents of the original query string.
    :param url: an URL string
    :param params: params to add as dict-like object
    """

    # idea from: http://stackoverflow.com/questions/2506379/add-params-to-given-url-in-python
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)

    url_parts[4] = urlencode_params_to_query(query)

    return urlparse.urlunparse(url_parts)