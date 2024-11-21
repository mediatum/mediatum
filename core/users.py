# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
from warnings import warn

import ipaddr as _ipaddr
import flask as _flask
import sqlalchemy as _syqlalchemy

import core as _core
import core.database.postgres.user as _
import core.database.postgres as _

logg = logging.getLogger(__name__)

# permission check functions for the access types
access_funcs = {
    "read": _core.database.postgres.mediatumfunc.has_read_access_to_node,
    "write": _core.database.postgres.mediatumfunc.has_write_access_to_node,
    "data": _core.database.postgres.mediatumfunc.has_data_access_to_node
}

def create_user(name, email, groups, pwd="", lastname="", firstname="", telephone="",
                comment="", option="", organisation="", identificator="", type="intern"):
    raise Exception("use constructor of User model class")


def getExternalUsers(atype=""):
    raise Exception("we don't need this anymore")


def getExternalUser(name, type="intern"):
    raise Exception("we don't need this anymore")


def get_guest_user():
    return _core.database.postgres.user.GuestUser.get()


def getUser(name_or_id):
    """Returns user object from db if found, else None"""
    try:
        nid = long(name_or_id)
    except ValueError:
        pass
    else:
        warn("use q(User).get(id)", DeprecationWarning)
        return _core.db.query(_core.database.postgres.user.User).get(nid)

    warn("use q(User).filter_by(login_name=login_name)", DeprecationWarning)
    return _core.db.query(_core.database.postgres.user.User).filter_by(login_name=name_or_id).scalar()


def getExternalAuthentificator(name):
    raise Exception("use auth.authenticators")


def getExternalAuthentificators():
    raise Exception("use auth.authenticators")


def user_from_session():

    user_from_cache = _flask.g.mediatum.get("user")
    if user_from_cache is not None:
        return user_from_cache
    
    def _user_from_session():
        user_id = _flask.session.get("user_id")
        if user_id is not None:
            user = _core.db.query(_core.database.postgres.user.User).get(user_id)

            if user is not None:
                return user

            logg.warning("invalid user id %s from session, falling back to guest user", user_id)
            del _flask.session["user_id"]

        return get_guest_user()
    
    user = _user_from_session()
    _flask.g.mediatum["user"] = user
    return user


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


def has_access_to_node_id(node_id, accesstype, user=None, ip=None, date=None):
    from core import db
    from core.users import get_guest_user

    if user is None:
        user = get_guest_user()

    if user.is_admin:
        return True

    if ip is None:
        ip = _ipaddr.IPv4Address("0.0.0.0")

    if date is None:
        date = _syqlalchemy.func.current_date()

    accessfunc = access_funcs[accesstype]
    group_ids = user.group_ids
    access = accessfunc(node_id, group_ids, ip, date)
    return db.session.execute(_syqlalchemy.select([access])).scalar()
