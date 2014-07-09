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
from core.transition import httpstatus
import core.users as users
import web.admin.modules.user as usermodule

import core.config as config
import core.tree as tree

import logging
import random
import hashlib

import utils.mail as mail
import utils.date as date

from web.frontend.frame import getNavigationFrame
from core.translation import lang, t
from utils.utils import mkKey
from core.styles import theme


def buildURL(req):
    p = ""
    for key in req.params:
        p += "&" + str(key) + "=" + req.params.get(key)
    req.request["Location"] = "http://" + config.get("host.name") + "/node?" + p[1:]
    return httpstatus.HTTP_MOVED_TEMPORARILY


def login(req):
    
    if len(req.params) > 2 and "user" not in req.params:  # user changed to browsing
        return buildURL(req)

    error = 0
    username = req.params.get("user", config.get("user.guestuser"))
    password = req.params.get("password", "")

    if username == "" and "user" in req.params:  # empty username
        error = 1

    elif "LoginSubmit" in req.params:  # try given values

        user = users.checkLogin(username, password, req=req)

        if user:
            if "contentarea" in req.session:
                del req.session["contentarea"]
            req.session["user"] = user
            logging.getLogger('usertracing').info(user.name + " logged in")

            if user.getUserType() == "users":
                if user.stdPassword():
                    return pwdchange(req, 3)

            else:
                x = users.getExternalAuthentificator(user.getUserType())
                if x and x.stdPassword(user):
                    return pwdchange(req, 3)

            if req.session['return_after_login']:
                req.request['Location'] = req.session['return_after_login']
            elif config.get("config.ssh", "") == "yes":
                req.request["Location"] = ''.join(["https://",
                                                   config.get("host.name"),
                                                   "/node?id=",
                                                   tree.getRoot("collections").id])
            else:
                req.request["Location"] = ''.join(["/node?id=",
                                                   tree.getRoot("collections").id])
            return httpstatus.HTTP_MOVED_TEMPORARILY
        else:
            error = 1

    if any(uri in req.header[6] for uri in ('/login', '/logout', '/pwdforgotten', '/pwdchange', '/pnode')) or 'Referer' not in req.header[6]:
        req.session['return_after_login'] = False
    else:
        if '/edit' in req.header[6]:
            #returns the user to /edit/ instead of /edit/edit_content?id=604993, which has no sidebar
            req.session['return_after_login'] = '/'.join(req.header[6]
                                                         .split(': ')[-1]
                                                         .split('/')[:-1])
        else:
            req.session['return_after_login'] = req.header[6].split(': ')[-1]

    # standard login form
    user = users.getUserFromRequest(req)
    navframe = getNavigationFrame(req)
    navframe.feedback(req)
    navframe.write(req, req.getTAL(theme.getTemplate("login.html"), {"error": error, "user": user}, macro="login"))
    return httpstatus.HTTP_OK


def logout(req):
    # if the session has expired, there may be no user in the session dictionary
    user = req.session.get("user", None)
    if user and user.getUserType() in users.getDynamicUserAuthenticators():
        users.authenticators[user.getUserType()].log_user_out(user.dirid, req.session.id)
    try:
        del req.session["user"]
    except:
        pass
    req.request["Location"] = req.makeLink("node", {"id": tree.getRoot("collections").id})
    return httpstatus.HTTP_MOVED_TEMPORARILY


def pwdchange(req, error=0):
    if len(req.params) > 2 and "password_old" not in req.params:  # user changed to browsing
        return buildURL(req)

    user = users.getUserFromRequest(req)

    if not user.canChangePWD() and not user.isAdmin():
        error = 4  # no rights

    elif "ChangeSubmit" in req.params:
        if user.getName() == config.get("user.guestuser"):
            req.request["Location"] = req.makeLink("node", {"id": tree.getRoot("collections").id})
            return httpstatus.HTTP_MOVED_TEMPORARILY

        else:
            if not users.checkLogin(user.getName(), req.params.get("password_old")):
                error = 1  # old pwd does not match

            elif req.params.get("password_new1") != req.params.get("password_new2"):
                error = 2  # new pwds do not match

            else:
                user.setPassword(req.params.get("password_new2"))
                req.request["Location"] = req.makeLink("node", {"id": tree.getRoot("collections").id})
                return httpstatus.HTTP_MOVED_TEMPORARILY

    navframe = getNavigationFrame(req)
    navframe.feedback(req)
    contentHTML = req.getTAL(theme.getTemplate("login.html"), {"error": error, "user": user}, macro="change_pwd")
    navframe.write(req, contentHTML)
    return httpstatus.HTTP_OK


def pwdforgotten(req):
    if len(req.params) > 3:  # user changed to browsing
        return buildURL(req)

    navframe = getNavigationFrame(req)
    navframe.feedback(req)

    if req.params.get("action", "") == "activate":  # do activation of new password
        id, key = req.params.get("key").replace("/", "").split('-')
        targetuser = users.getUser(id)

        if targetuser.get("newpassword.activation_key") == key:
            newpassword = targetuser.get("newpassword.password")

            if newpassword:
                targetuser.set("password", newpassword)
                print "password reset for user '%s' (id=%s) reset" % (targetuser.getName(), targetuser.id)
                targetuser.removeAttribute("newpassword.password")
                targetuser.set("newpassword.time_activated", date.format_date())
                logging.getLogger('usertracing').info("new password activated for user: %s - was requested: %s by %s" % (targetuser.getName(), targetuser.get("newpassword.time_requested"), targetuser.get("newpassword.request_ip")))

                navframe.write(req, req.getTAL(theme.getTemplate("login.html"), {"username": targetuser.getName()}, macro="pwdforgotten_password_activated"))
                return httpstatus.HTTP_OK

            else:
                print "invalid key: wrong key or already used key"
                navframe.write(req, req.getTAL(theme.getTemplate("login.html"), {"message": "pwdforgotten_password_invalid_key"}, macro="pwdforgotten_message"))
                return httpstatus.HTTP_OK

    elif "user" in req.params:  # create email with activation information
        username = req.params.get("user", "")

        if username == '':
            req.params['error'] = "pwdforgotten_noentry"

        else:
            targetuser = users.getUser(username)

            if not targetuser or not targetuser.canChangePWD():
                logging.getLogger('usertracing').info("new password requested for non-existing user: " + username)
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
                    logging.getLogger('usertracing').info("new password requested for user: %s - activation email sent" % username)
                    navframe.write(req, req.getTAL(theme.getTemplate("login.html"), {"message": "pwdforgotten_butmailnowsent"}, macro="pwdforgotten_message"))
                    return httpstatus.HTTP_OK

                except mail.SocketError:
                    print "Socket error while sending mail"
                    logging.getLogger('usertracing').info("new password requested for user: %s - failed to send activation email" % username)
                    return req.getTAL(theme.getTemplate("login.html"), {"message": "pwdforgotten_emailsenderror"}, macro="pwdforgotten_message")

    # standard operation
    navframe.write(req, req.getTAL(theme.getTemplate("login.html"), {"error": req.params.get("error"), "user": users.getUserFromRequest(req)}, macro="pwdforgotten"))
    return httpstatus.HTTP_OK
