# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division

from contextlib import contextmanager

import requests
from nap.url import Url


class SessionUrl(Url):

    """Extends the Url class with a persistent requests session
    """

    def __init__(self, base_url, **default_kwargs):
        super(SessionUrl, self).__init__(base_url, **default_kwargs)
        self.session = None

    def new_session(self, **session_options):
        if self.session is not None:
            self.finish_session()
        self.session = requests.session()

    @contextmanager
    def session_context(self, **session_options):
        self.new_session(**session_options)
        yield self.session
        self.finish_session()

    def finish_session(self):
        self.session.close()
        self.session = None

    def _request(self, http_method, relative_url='', **kwargs):
        """Does actual HTTP request using requests library."""
        # It could be possible to call api.resource.get('/index')
        # but it would be non-intuitive that the path would resolve
        # to root of domain
        relative_url = self._remove_leading_slash(relative_url)

        # Add default kwargs with possible custom kwargs returned by
        # before_request
        new_kwargs = self.default_kwargs().copy()
        custom_kwargs = self.before_request(
            http_method,
            relative_url,
            kwargs.copy()
        )
        new_kwargs.update(custom_kwargs)

        r = self.session or requests
        response = r.request(
            http_method,
            self._join_url(relative_url),
            **new_kwargs
        )

        return self.after_request(response)
