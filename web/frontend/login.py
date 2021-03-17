"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import division
from __future__ import print_function

import logging
import hashlib
import flask as _flask

from core import db, User, auth
from core import httpstatus
from core.webconfig import node_url
import core.users as users
import core.config as config
from core.nodecache import get_collections_node
import utils.mail as mail
import utils.date as date
from web.frontend import frame
from core.translation import lang, t
from utils.utils import mkKey
from core import webconfig
from core.auth import PasswordsDoNotMatch, WrongPassword, PasswordChangeNotAllowed
from core.users import get_guest_user
from datetime import datetime
from mediatumtal import tal

q = db.query
logg = logging.getLogger(__name__)


_collection_root_link = None


def _make_collection_root_link():
    global _collection_root_link

    if _collection_root_link is None:
        _collection_root_link = node_url(get_collections_node().id)

    return _collection_root_link


def _handle_login_submit(req):
    login_name = req.form.get("user")
    password = req.form.get("password", "")
    return_after_login = req.form.get("return_after_login")

    if not login_name.strip() and "user" in req.form:
        # empty username
        return 1

    user = auth.authenticate_user_credentials(login_name, password, req)
    if user:
        # stop caching
        req.response.set_cookie("nocache", "1")
        _flask.session["user_id"] = user.id
        logg.info("%s logged in", user.login_name)

        if return_after_login:
            req.response.location = return_after_login
        elif config.get("config.ssh", "") == "yes":
            req.response.location = ''.join(["https://", config.get("host.name"), _make_collection_root_link()])
        else:
            req.response.location = _make_collection_root_link()

        # stores the date/time when a user logs in except in read-only mode
        if not config.getboolean("config.readonly", False):
            user.last_login = datetime.now()
            db.session.commit()
    else:
        return 1


def _set_return_after_login(req):
    referer = req.referrer
    host = req.host

    if referer is None or any(uri in referer for uri in ('/login', '/logout', '/pwdforgotten', '/pwdchange', '/pnode')):
        return_after_login = False
    # check if referrer is mediatum and not a search engine
    elif not referer.startswith('http://' + host + '/') and not referer.startswith('https://' + host + '/'):
        return_after_login = False
    else:
        if '/edit_content' in referer:
            # returns the user to /edit/ instead of /edit/edit_content?id=604993, which has no sidebar
            return_after_login = referer.replace("/edit_content", "")
        else:
            return_after_login = referer

    return return_after_login


def login(req):

    if "LoginSubmit" in req.form:
        error = _handle_login_submit(req)
        if not error:
            req.response.status_code = httpstatus.HTTP_MOVED_TEMPORARILY
            return httpstatus.HTTP_MOVED_TEMPORARILY
    else:
        error = None

    return_after_login = _set_return_after_login(req)

    # show login form
    user = users.user_from_session()
    language = lang(req)
    ctx = dict(
        error=error,
        user=user,
        email=config.get("email.support"),
        language=language,
        return_after_login=return_after_login,
        csrf=req.csrf_token.current_token,
    )
    login_html = webconfig.theme.render_macro("login.j2.jade", "login", ctx)
    from web.frontend.frame import render_page
    html = render_page(req, login_html)
    req.response.status_code = httpstatus.HTTP_OK
    req.response.set_data(html)
    return httpstatus.HTTP_OK


def logout(req):
    # if the session has expired, there may be no user in the session dictionary
    user = users.user_from_session()
    if not user.is_anonymous:
        auth.logout_user(user, req)
        if "user_id" in _flask.session:
            del _flask.session["user_id"]

    req.response.location = '/'
    req.response.status_code = httpstatus.HTTP_MOVED_TEMPORARILY
    # return to caching
    req.response.set_cookie("nocache", "0")
    return httpstatus.HTTP_MOVED_TEMPORARILY


def pwdchange(req):
    user = users.user_from_session()
    error = 0

    if "ChangeSubmit" in req.form:
        if user.is_anonymous:
            req.response.location = _make_collection_root_link()
            req.response.status_code = httpstatus.HTTP_MOVED_TEMPORARILY
            return httpstatus.HTTP_MOVED_TEMPORARILY

        else:
            password_old = req.form.get("password_old")
            password_new1 = req.form.get("password_new1")
            password_new2 = req.form.get("password_new2")

            try:
                auth.change_user_password(user, password_old, password_new1, password_new2, req)
            except WrongPassword:
                error = 1
            except PasswordsDoNotMatch:
                error = 2
            except PasswordChangeNotAllowed:
                error = 4
            else:
                req.response.location = _make_collection_root_link()
                req.response.autocorrect_location_header = False
                req.response.status_code = httpstatus.HTTP_MOVED_TEMPORARILY
                return httpstatus.HTTP_MOVED_TEMPORARILY

    content_html = webconfig.theme.render_macro("login.j2.jade", "change_pwd", {"error": error, "user": user, "csrf": req.csrf_token.current_token})
    from web.frontend.frame import render_page
    html = render_page(req, content_html)
    req.response.set_data(html)
    req.response.status_code = httpstatus.HTTP_OK
    return httpstatus.HTTP_OK


def pwdforgotten(req):
    raise NotImplementedError("must be rewritten")
