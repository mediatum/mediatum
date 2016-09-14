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
import logging
import hashlib

from core import db, User, auth
from core.transition import httpstatus
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
from web.frontend.frame import render_page

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

    if not login_name.strip() and "user" in req.form:
        # empty username
        return 1

    user = auth.authenticate_user_credentials(login_name, password, req)
    if user:
        # stop caching
        req.setCookie("nocache", "1", path="/")
        if "contentarea" in req.session:
            del req.session["contentarea"]
        req.session["user_id"] = user.id
        logg.info("%s logged in", user.login_name)

        if req.session.get('return_after_login'):
            req['Location'] = req.session['return_after_login']
        elif config.get("config.ssh", "") == "yes":
            req["Location"] = ''.join(["https://", config.get("host.name"), _make_collection_root_link()])
        else:
            req["Location"] = _make_collection_root_link()

        # stores the date/time when a user logs in except in read-only mode
        if not config.getboolean("config.readonly", False):
            user.last_login = datetime.now()
            db.session.commit()
    else:
        return 1


def _set_return_after_login(req):
    referer = req.get_header("Referer")

    if referer is None or any(uri in referer for uri in ('/login', '/logout', '/pwdforgotten', '/pwdchange', '/pnode')):
        req.session['return_after_login'] = False
    else:
        if '/edit_content' in referer:
            # returns the user to /edit/ instead of /edit/edit_content?id=604993, which has no sidebar
            req.session['return_after_login'] = referer.replace("/edit_content", "")
        else:
            req.session['return_after_login'] = referer


def login(req):

    if "LoginSubmit" in req.form:
        error = _handle_login_submit(req)
        if not error:
            return httpstatus.HTTP_MOVED_TEMPORARILY
    else:
        error = None

    _set_return_after_login(req)

    # show login form
    user = users.user_from_session(req.session)
    ctx = {"error": error, "user": user, "email": config.get("email.support")}
    login_html = tal.getTAL(webconfig.theme.getTemplate("login.html"), ctx, macro="login", language=lang(req))
    html = render_page(req, None, login_html)
    req.write(html)
    return httpstatus.HTTP_OK


def logout(req):
    # if the session has expired, there may be no user in the session dictionary
    user = users.user_from_session(req.session)
    if not user.is_anonymous:
        auth.logout_user(user, req)
        if "user_id" in req.session:
            del req.session["user_id"]

    req.request["Location"] = '/'
    # return to caching
    req.setCookie("nocache", "0", path="/")
    return httpstatus.HTTP_MOVED_TEMPORARILY


def pwdchange(req):
    user = users.user_from_session(req.session)
    error = 0

    if "ChangeSubmit" in req.form:
        if user.is_anonymous:
            req.request["Location"] = _make_collection_root_link()
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
                req["Location"] = _make_collection_root_link()
                return httpstatus.HTTP_MOVED_TEMPORARILY

    content_html = tal.getTAL(webconfig.theme.getTemplate("login.html"), {"error": error, "user": user}, macro="change_pwd", language=lang(req))
    html = render_page(req, None, content_html)
    req.write(html)
    return httpstatus.HTTP_OK


def pwdforgotten(req):
    raise NotImplementedError("must be rewritten")
