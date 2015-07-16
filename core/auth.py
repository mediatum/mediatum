# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from base64 import b64encode
import logging
import os
import hashlib
from collections import OrderedDict
import scrypt
from core import db, config, AuthenticatorInfo, User

q = db.query

logg = logging.getLogger(__name__)

INTERNAL_AUTHENTICATOR_KEY = ("internal", "default")

# OrderedDict (auth_type, name): authenticator
authenticators = OrderedDict()


def generate_salt():
    return b64encode(os.urandom(16))[:-2]

def check_user_password(user, password):
    return user.password_hash == b64encode(scrypt.hash(password.encode("utf8"), str(user.salt)))

def create_password_hash(password):
    salt = generate_salt()
    password_hash = b64encode(scrypt.hash(password.encode("utf8"), salt))
    return (password_hash, salt)


class CredentialsError(ValueError):
    pass


class PasswordsDoNotMatch(CredentialsError):
    pass


class WrongPassword(CredentialsError):
    pass


class PasswordChangeNotAllowed(CredentialsError):
    pass
    

class Authenticator(object):

    def __init__(self, name):
        self.name = name

    def authenticate_user_credentials(self, login, password, request):
        """Returns an User instance when authentication succeeds, else None."""

    def logout_user(self, user, request):
        """Performs logout for given `user`
        """

    def change_user_password(self, user, old_password, new_password, request):
        """Sets a `new_password` for `user` if `old_password` is correct.
        """


class InternalAuthenticator(Authenticator):

    auth_type = INTERNAL_AUTHENTICATOR_KEY[0]

    def authenticate_user_credentials(self, login_name, password, request):
        """Returns an User instance when authentication with `login_name` and `password` succeeds, else None.
        Successful means: login and password hash match the db values
        """
        user = (
            q(User).filter_by(login_name=login_name)
            .join(AuthenticatorInfo).filter_by(auth_type=InternalAuthenticator.auth_type, name=self.name).scalar()
        )

        if user is not None:
            if user.salt:
                if check_user_password(user, password):
                    return user
            else:
                if user.password_hash == hashlib.md5(password).hexdigest():
                    # rehash password
                    user.change_password(password)
                    logg.info("rehashed password for user '%s'", user.login_name)
                    db.session.commit()
                    return user

    def change_user_password(self, user, old_password, new_password, request):
        if not check_user_password(user, old_password):
            raise WrongPassword()

        user.change_password(new_password)
        db.session.commit()

    def create_user(self, login_name, password, **kwargs):
        password_hash, salt = create_password_hash(password)
        authenticator_id = q(AuthenticatorInfo.id).filter_by(auth_type=InternalAuthenticator.auth_type, name=self.name).scalar()
        user = User(login_name=login_name, password_hash=password_hash, salt=salt, authenticator_id=authenticator_id, **kwargs)
        db.session.add(user)
        return user


def register_authenticator(authenticator, name=""):
    """authenticators can have a name to distinquish between instances of the same auth_type
    """
    key = (authenticator.auth_type, name)
    # re-sort authenticators according to configured order
    auth_order = config.get("auth.authenticator_order", ("internal", ""))
    existing_authenticators = authenticators
    authenticators = OrderedDict()

    for order_key in auth_order:
        if order_key == key:
            authenticators[order_key] = authenticator
        else:
            authenticators[order_key] = existing_authenticators[order_key]

    logg.info("registered authenticator auth_type %s, name %s", authenticator.auth_type, name)


def authenticate_user_credentials(login, password, request):
    """Queries registered authenticators with given credentials in order defined by configuration.
    If an authenticator succeeds, immediately return the resulting user or None, if all fail.
    XXX: can we remove request?
    """
    for authenticator in authenticators.values():
        user = authenticator.authenticate_user_credentials(login, password, request)
        if user is not None:
            return user


def logout_user(user, request):
    authenticator = authenticators[user.authenticator_info.authenticator_key]
    return authenticator.logout_user(user, request)


def change_user_password(user, old_password, new_password, new_password_repeated, request=None):
    if not user.can_change_password:
        raise PasswordChangeNotAllowed()
    if new_password != new_password_repeated:
        raise PasswordsDoNotMatch()
    
    authenticator = authenticators[user.authenticator_info.authenticator_key]
    return authenticator.change_user_password(user, old_password, new_password, request)


def init():
    # if authenticator_order is undefined, use an internal authentificator only
    # internal auth can be disabled by not adding it to the config option
    auth_order = config.get("auth.authenticator_order", [INTERNAL_AUTHENTICATOR_KEY])
    if INTERNAL_AUTHENTICATOR_KEY in auth_order:
        authenticators[INTERNAL_AUTHENTICATOR_KEY] = InternalAuthenticator(name=INTERNAL_AUTHENTICATOR_KEY[1])
