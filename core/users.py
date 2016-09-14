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
from warnings import warn

import core.config as config
from core import User
from core import db
from core.user import GuestUser


logg = logging.getLogger(__name__)
q = db.query


def create_user(name, email, groups, pwd="", lastname="", firstname="", telephone="",
                comment="", option="", organisation="", identificator="", type="intern"):
    raise Exception("use constructor of User model class")


def getExternalUsers(atype=""):
    raise Exception("we don't need this anymore")


def getExternalUser(name, type="intern"):
    raise Exception("we don't need this anymore")


def get_guest_user():
    return GuestUser.get()


def getUser(name_or_id):
    """Returns user object from db if found, else None"""
    try:
        nid = long(name_or_id)
    except ValueError:
        pass
    else:
        warn("use q(User).get(id)", DeprecationWarning)
        return q(User).get(nid)

    warn("use q(User).filter_by(login_name=login_name)", DeprecationWarning)
    return q(User).filter_by(login_name=name_or_id).scalar()


def getExternalAuthentificator(name):
    raise Exception("use auth.authenticators")


def getExternalAuthentificators():
    raise Exception("use auth.authenticators")


def user_from_session(session):
    
    from core.transition import request
    user_from_cache = request.app_cache.get("user")
    if user_from_cache is not None:
        return user_from_cache
    
    def _user_from_session():
        user_id = session.get("user_id")
        if user_id is not None:
            user = q(User).get(user_id)

            if user is not None:
                return user

            logg.warn("invalid user id %s from session, falling back to guest user", user_id)
            del session["user_id"]

        return get_guest_user()
    
    user = _user_from_session()
    request.app_cache["user"] = user
    return user


def getUserFromRequest(req):
    warn("use users.user_from_session()", DeprecationWarning)
    return user_from_session(req.session)


def getExternalUserFolder(type=""):
    raise Exception("we don't need this anymore")


def checkLogin(name, pwd, req=None):
    raise Exception("use auth.authenticate_user_credentials()")


def update_user(id, name, email, groups, lastname="", firstname="", telephone="",
                comment="", option="", organisation="", identificator="", type="intern"):
    raise Exception("this needs a complete rewrite")


def deleteUser(user, usertype="intern"):
    raise Exception("this needs a complete rewrite")


def existUser(username):
    raise Exception("use q(User).filter_by(login_name=login_name)")


def makeRandomPassword():
    raise Exception("please, don't use this...")


def registerAuthenticator(auth, name, priority=0):
    raise Exception("use auth.register_authenticator()")


def moveUserToIntern(id):
    raise Exception("we must implement something different...")


def getHideMenusForUser(user):
    warn("use User.hidden_edit_functions", DeprecationWarning)
    return user.hidden_edit_functions


def getHomeDir(user):
    warn("use User.home_dir (User.create_home_dir() if user has no home)", DeprecationWarning)
    return user.home_dir


def getSpecialDir(user, type):
    warn("use User.upload_dir | User.trash_dir instead", DeprecationWarning)
    if type == "upload":
        return user.upload_dir
    elif type == "trash":
        return user.trash_dir


def getUploadDir(user):
    return getSpecialDir(user, "upload")


def getTrashDir(user):
    return getSpecialDir(user, "trash")
