# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
move get_nodes_per_page from web/edit/edit_common.py. Parameters are nodes_per_page
from request parameters or dir as node. default_edit_nodes_per_page is returned in case
parameter is not given.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import datetime as _datetime
import wtforms.csrf.session as _wtform_csrf_session
from wtforms import Form as _wtforms_Form
import flask as _flask

import core.config as _core_config


class CSRFForm(_wtforms_Form):
    """
     CSRF implementation for session-based hash secure keying, which puts CSRF data in a session
    """
    class Meta:
        """
        CSRF in WTForms 2.0 is driven through a number of variables on class Meta
        """
        csrf = True
        csrf_class = _wtform_csrf_session.SessionCSRF

        @property
        def csrf_context(self):
            return _flask.session

        @property
        def csrf_secret(self):
            return _core_config.get_secret_key('csrf.secret_key_file', uwsgi_cache_key='csrf_secret_key')

        @property
        def csrf_time_limit(self):
            return _datetime.timedelta(seconds=_core_config.getint('csrf.timeout', 0)) or None


def get_token():
    """
    This function may be called multiple times within a
    request -- it will cache its result and serve the same token.
    """
    if "csrf_token" in _flask.g.mediatum:
        return _flask.g.mediatum["csrf_token"]
    else:
        form_obj = CSRFForm()  # this adds csrf-info to session cookie
        return _flask.g.mediatum.setdefault("csrf_token", form_obj.csrf_token.current_token)


def validate_token(form_data):
    """
    If the current request answers a form,
    ensure that a valid csrf-token is part of the form.
    Return a csrf-token to be included in another
    form that is being served as response,
    also put the relevant validation information
    into the session cookie.
    `form_data` is the `request.form` object.
    """
    form_obj = CSRFForm()  # this adds csrf-info to session cookie
    csrf_token = form_data.get("csrf_token")
    if not csrf_token:
        raise ValueError("csrf_token not in form !!!")
    form_obj.csrf_token.process_data(csrf_token.replace("!!!!!", "##"))
    if not form_obj.validate():
        raise ValueError("csrf_token validation failed !!!")

    _flask.g.mediatum.setdefault("csrf_token", form_obj.csrf_token.current_token)
