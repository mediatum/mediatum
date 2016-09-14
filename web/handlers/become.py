# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import logging
import re
from core.transition import current_user, httpstatus
import web.admin.adminutils


logg = logging.getLogger(__name__)

BECOME_RE = re.compile("/_become/([^/]+)/?([^/]+)?$")


def become_user(req):
    if not current_user.is_admin:
        return 404

    before_user_id = current_user.id

    match = BECOME_RE.match(req.path)
    if match:
        p1, p2 = match.groups()
        if p1 and p2:
            authenticator_key, login_name = p1, p2
        else:
            login_name, authenticator_key = p1, None
    else:
        logg.warn("become_user handler: bad request from user %s, path %s", before_user_id, req.path)
        return 400

    try:
        user = web.admin.adminutils.become_user(login_name, authenticator_key)
    except Exception as e:
        logg.exception("become_user handler: becoming user failed for user %s, path %s", before_user_id, req.path)
        return 400

    if user is not None:
        logg.info("admin user %s became user %s", before_user_id, user.id)
    else:
        logg.info("become user handler: user with login_name %s not found", login_name)

    req["Location"] = "/"
    return httpstatus.HTTP_MOVED_TEMPORARILY