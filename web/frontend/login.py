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
import core.users as users
import core.config as config
import utils.mail as mail
import utils.date as date
from web.frontend import frame
from core.translation import lang, t
from utils.utils import mkKey
from core.styles import theme
from contenttypes import Collections

q = db.query
logg = logging.getLogger(__name__)


def _make_collection_root_link():
    return "/node?id={}".format(q(Collections).one().id)


def _handle_login_submit(req):
    login_name = req.form.get("user", config.get("user.guestuser"))
    password = req.form.get("password", "")

    if not login_name.strip() and "user" in req.form:  
        # empty username
        return 1

    user = auth.authenticate_user_credentials(login_name, password, req)
    if user:
        if "contentarea" in req.session:
            del req.session["contentarea"]
        req.session["user"] = user
        logg.info("%s logged in", user.login_name)

        if req.session.get('return_after_login'):
            req['Location'] = req.session['return_after_login']
        elif config.get("config.ssh", "") == "yes":
            req["Location"] = ''.join(["https://",
                                       config.get("host.name"),
                                       "/node?id=",
                                       q(Collections).one().id])
        else:
            req["Location"] = _make_collection_root_link()
    else:
        return 1


def _set_return_after_login(req):
    referer = next((h.split(":", 1)[1].strip() for h in req.header if h.startswith("Referer:")), None)

    if referer is None or any(uri in referer for uri in ('/login', '/logout', '/pwdforgotten', '/pwdchange', '/pnode')):
        req.session['return_after_login'] = False
    else:
        if '/edit' in referer:
            # returns the user to /edit/ instead of /edit/edit_content?id=604993, which has no sidebar
            req.session['return_after_login'] = '/'.join(referer
                                                         .split('/')[:-1])
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
    navframe = frame.getNavigationFrame(req)
    navframe.feedback(req)
    navframe.write(req, req.getTAL(theme.getTemplate("login.html"), {"error": error, "user": user}, macro="login"))
    return httpstatus.HTTP_OK


def logout(req):
    # if the session has expired, there may be no user in the session dictionary
    user = users.user_from_session(req.session)
    auth.logout_user(user, req)
    if "user" in req.session:
        del req.session["user"]

    req.request["Location"] = '/'
    return httpstatus.HTTP_MOVED_TEMPORARILY


def pwdchange(req, error=0):
    raise NotImplementedError()

    user = users.getUserFromRequest(req)

    if not user.canChangePWD() and not user.isAdmin():
        error = 4  # no rights

    elif "ChangeSubmit" in req.params:
        if user.getName() == config.get("user.guestuser"):
            req.request["Location"] = _make_collection_root_link()
            return httpstatus.HTTP_MOVED_TEMPORARILY

        else:
            if not users.checkLogin(user.getName(), req.params.get("password_old")):
                error = 1  # old pwd does not match

            elif req.params.get("password_new1") != req.params.get("password_new2"):
                error = 2  # new pwds do not match

            else:
                auth.change_user_password(req.params.get("password_new2"))
                req.request["Location"] = _make_collection_root_link()
                return httpstatus.HTTP_MOVED_TEMPORARILY

    navframe = frame.getNavigationFrame(req)
    navframe.feedback(req)
    contentHTML = req.getTAL(theme.getTemplate("login.html"), {"error": error, "user": user}, macro="change_pwd")
    navframe.write(req, contentHTML)
    return httpstatus.HTTP_OK


def pwdforgotten(req):
    raise NotImplementedError()

    navframe = frame.getNavigationFrame(req)
    navframe.feedback(req)

    if req.params.get("action", "") == "activate":  # do activation of new password
        id, key = req.params.get("key").replace("/", "").split('-')
        targetuser = users.getUser(id)

        if targetuser.get("newpassword.activation_key") == key:
            newpassword = targetuser.get("newpassword.password")

            if newpassword:
                targetuser.set("password", newpassword)
                logg.info("password reset for user '%s' (id=%s) reset", targetuser.name, targetuser.id)
                targetuser.removeAttribute("newpassword.password")
                targetuser.set("newpassword.time_activated", date.format_date())
                logg.info("new password activated for user: %s - was requested: %s by %s",
                          targetuser.name, targetuser.get("newpassword.time_requested"), targetuser.get("newpassword.request_ip"))

                navframe.write(
                    req, req.getTAL(
                        theme.getTemplate("login.html"), {
                            "username": targetuser.getName()}, macro="pwdforgotten_password_activated"))
                return httpstatus.HTTP_OK

            else:
                logg.error("invalid key: wrong key or already used key")
                navframe.write(
                    req, req.getTAL(
                        theme.getTemplate("login.html"), {
                            "message": "pwdforgotten_password_invalid_key"}, macro="pwdforgotten_message"))
                return httpstatus.HTTP_OK

    elif "user" in req.params:  # create email with activation information
        username = req.params.get("user", "")

        if username == '':
            req.params['error'] = "pwdforgotten_noentry"

        else:
            targetuser = users.getUser(username)

            if not targetuser or not targetuser.canChangePWD():
                logg.info("new password requested for non-existing user: %s", username)
                req.params['error'] = "pwdforgotten_nosuchuser"

            else:
                password = users.makeRandomPassword()
                randomkey = mkKey()

                targetuser.set("newpassword.password", hashlib.md5(password).hexdigest())
                targetuser.set("newpassword.time_requested", date.format_date())
                targetuser.set("newpassword.activation_key", randomkey)
                targetuser.set("newpassword.request_ip", req.ip)

                v = {}
                v["name"] = targetuser.getName()
                v["host"] = config.get("host.name")
                v["login"] = targetuser.getName()
                v["language"] = lang(req)
                v["activationlink"] = v["host"] + "/pwdforgotten?action=activate&key=%s-%s" % (targetuser.id, randomkey)
                v["email"] = targetuser.getEmail()
                v["userid"] = targetuser.getName()

                # going to send the mail
                try:
                    mailtext = req.getTAL(theme.getTemplate("login.html"), v, macro="emailtext")
                    mailtext = mailtext.strip().replace("[$newpassword]", password).replace("[wird eingesetzt]", password)

                    mail.sendmail(config.get("email.admin"), targetuser.getEmail(), t(lang(req), "pwdforgotten_email_subject"), mailtext)
                    logg.info("new password requested for user: %s - activation email sent", username)
                    navframe.write(
                        req, req.getTAL(
                            theme.getTemplate("login.html"), {
                                "message": "pwdforgotten_butmailnowsent"}, macro="pwdforgotten_message"))
                    return httpstatus.HTTP_OK

                except mail.SocketError:
                    logg.exception("new password requested for user: %s - failed to send activation email", username)
                    return req.getTAL(
                        theme.getTemplate("login.html"), {"message": "pwdforgotten_emailsenderror"}, macro="pwdforgotten_message")

    # standard operation
    navframe.write(req, req.getTAL(theme.getTemplate("login.html"), {
                   "error": req.params.get("error"), "user": users.getUserFromRequest(req)}, macro="pwdforgotten"))
    return httpstatus.HTTP_OK
